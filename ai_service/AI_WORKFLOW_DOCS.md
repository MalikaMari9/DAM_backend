# BreatheEasy AI Chat System — Technical Documentation

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Request Flow](#request-flow)
3. [Intent Parsing Engine](#intent-parsing-engine)
4. [PM2.5 Prediction Model (XGBoost)](#pm25-prediction-model-xgboost)
5. [Health Impact Engine (IER/PAF)](#health-impact-engine-ierpaf)
6. [Executive Analytics Layer](#executive-analytics-layer)
7. [Region Resolution](#region-resolution)
8. [Confidence & Uncertainty](#confidence--uncertainty)
9. [Data Files](#data-files)
10. [API Reference](#api-reference)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (app.py)                     │
│                     http://localhost:9000                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  POST /api/chat  ──►  QueryParser  ──►  RegionResolver          │
│       │                                      │                  │
│       ▼                                      ▼                  │
│  Intent Dispatch  ──────────────────►  Executive Layer           │
│       │                                      │                  │
│       │    ┌─────────────────────────────────┤                  │
│       │    │                                 │                  │
│       │    ▼                                 ▼                  │
│       │  predict_pm25.py              predict_health.py          │
│       │  (XGBoost Model)              (IER Health Engine)        │
│       │    │                                 │                  │
│       │    ▼                                 ▼                  │
│       │  scenario.py   trend.py   risk.py   analytics.py         │
│       │  explainability.py   uncertainty.py                      │
│       │                                                         │
│       ▼                                                         │
│  formatter.py  ──►  JSON Response                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Request Flow

### Step 1: User Input

```
POST /api/chat
Content-Type: application/json

{
  "message": "What if PM2.5 drops 15% in Thailand in 2027?"
}
```

### Step 2: Entity Extraction (QueryParser)

The `QueryParser.parse()` method extracts entities from the raw text:

| Entity          | Method                              | Example                        |
|-----------------|-------------------------------------|--------------------------------|
| **Country**     | Fuzzy match against 278 known names | "Thailand" → `Thailand`        |
| **Year**        | Regex + relative resolution         | "2027" → `2027`                |
| **Region**      | `normalize_region()` from region_resolver | "European" → `Europe`    |
| **Percent**     | Regex `\d+\s*%`                     | "15%" → `15.0`                 |
| **Sign**        | Keyword detection                   | "drops" → `-1`, "rises" → `+1`|
| **Month**       | Month name lookup                   | "January" → `1`               |
| **Age group**   | Keywords                            | "elderly" → `elderly`          |
| **Disease**     | Match against 10 IER disease names  | "stroke" → `Stroke`           |

**Year resolution rules:**
- Explicit year: `2027` → 2027
- `next year` → current_year + 1
- `last year` → current_year - 1
- `this year` / `current year` → current_year
- `in N years` → current_year + N

### Step 3: Intent Matching (20 Rule Categories)

Rules are checked **top-to-bottom**, first match wins:

| Priority | Intent                       | Trigger Keywords                                           |
|----------|------------------------------|------------------------------------------------------------|
| **A1**   | `SCENARIO_PM25_CHANGE`       | `%`, `what if`, `reduce by`, `increase by`                 |
| **A2**   | `SENSITIVITY_PM25_DEATHS`    | `sensitive to PM`, `elasticity`, `per 1 µg`                |
| **A3**   | `LOWEST_HEALTH_BURDEN`       | `lowest/least` + `deaths/DALYs/burden`                     |
| **A4**   | `FASTEST_IMPROVEMENT_PM25`   | `improving fastest`, `most improved`                       |
| **A5**   | `STABILITY_PM25`             | `most stable`, `most volatile`, `volatility`               |
| **A6**   | `RANK_PM25`                  | `top N polluted`, `most polluted`, `highest PM2.5`         |
| **A7**   | `DEATHS_CHANGE_YOY`          | `deaths increase compared`, `YoY deaths`                   |
| **B8**   | `RISK_RANKING`               | `ranked by risk`, `risk ranking`, `regional risk`          |
| **B9**   | `HIGHEST_RISK_COUNTRY`       | `highest risk score`, `highest pollution risk`             |
| **B10**  | `HEALTH_DALYS`               | `DALYs`, `disability-adjusted`                             |
| **B11**  | `EXPLAINABILITY`             | `why is`, `drivers`, `assumptions`, `structural break`     |
| **B12**  | `RISK_LEVEL`                 | `risk level`, `risk tier`, `risk score`                    |
| **B13**  | `TREND_PM25`                 | `trend`, `trajectory`, `over the years`                    |
| **B14**  | `COMPARE_HEALTH`             | `compare`, `vs`, `versus`                                  |
| **B15**  | `PM25_CHANGE`                | `from 20XX to 20XX`, `since 20XX`, `change`                |
| **B16**  | `HEALTH_RATE`                | `per 100,000`, `death rate`                                |
| **B17**  | `HEALTH_DEATHS`              | `deaths`, `mortality`, `health impact`                     |
| **B18**  | `TOP_DISEASES`               | `top diseases`, `which diseases`                           |
| **B19**  | `BEST_MONTH` / `WORST_MONTH` | `best month`, `worst month`, `peak pollution`              |
| **B20**  | `PM25_FORECAST`              | *(fallback — any country + year)*                          |

### Step 4: Region Resolution

If user mentions a region, `resolve_region_countries()` maps it to dataset countries:

- **13 supported regions**: ASEAN, Europe, South Asia, East Asia, Southeast Asia, Africa, North America, South America, Central America, Caribbean, Middle East, Central Asia, Oceania
- **Adjective normalization**: "European" → Europe, "South Asian" → South Asia
- **Default scope**: Global (all 257 countries) — NOT limited to ASEAN
- **Error handling**: Unknown region returns clear error with supported region list

### Step 5: Intent Dispatch → Executive Functions → Formatted Response

`app.py` routes to the correct executive function, which returns a result dict. The formatter produces a human-readable text response.

---

## PM2.5 Prediction Model (XGBoost)

**Files:** `inference.py` → `PM25Predictor`, `executive/predict_pm25.py`

### Model Details

| Property         | Value                                          |
|------------------|-------------------------------------------------|
| Algorithm        | XGBoost (gradient boosted trees)                |
| Model file       | `models/xgboost_v20260213_104212.pkl`           |
| Training data    | PM2.5 history 2000–2019 (257 countries)         |
| Prediction range | Any year from 2020 onward                       |
| Minimum output   | TMREL = 5.0 µg/m³ (theoretical minimum risk)    |

### 7 Input Features

| # | Feature          | Description                                  |
|---|------------------|----------------------------------------------|
| 1 | `lag_1y`         | PM2.5 value 1 year before target             |
| 2 | `lag_3y`         | PM2.5 value 3 years before target            |
| 3 | `yoy_change`     | Absolute change from year-2 to year-1        |
| 4 | `yoy_pct_change` | Percentage change from year-2 to year-1      |
| 5 | `rolling_mean_3y`| 3-year rolling average                       |
| 6 | `rolling_mean_5y`| 5-year rolling average                       |
| 7 | `target_year`    | The year being predicted                     |

### Recursive Multi-Step Forecasting

The model predicts one year at a time, appending each prediction to the history before predicting the next. For a target year of 2027:

```
Historical data: 2000-2019 (known PM2.5 values)

Step 1: Build features from history → Predict 2020 → Append to history
Step 2: Build features from history+2020 → Predict 2021 → Append
Step 3: Build features from history+2020-2021 → Predict 2022 → Append
...
Step 8: Build features from history+2020-2026 → Predict 2027 → FINAL RESULT
```

Each prediction is **clamped** to the TMREL minimum (5.0 µg/m³).

### Monthly Predictions

Annual PM2.5 is adjusted by region-specific **seasonal multipliers**:
- **Southeast Asia**: peaks in Jan–Mar (burning season), lowest Jun–Jul
- **South Asia**: peaks in Nov–Feb (winter inversion)
- **East Asia**: peaks in Jan–Feb

Formula: `monthly_pm25 = annual_pm25 × seasonal_factor[month]`

### Key Functions

| Function                     | Description                                  |
|------------------------------|----------------------------------------------|
| `forecast_pm25(country, yr)` | Point prediction for one country/year        |
| `pm25_change(c, y1, y2)`    | Absolute + % change between two years        |
| `pm25_change_vs_last_year()` | YoY % change with ↑/↓/→ arrow                |
| `get_pm25_history(country)`  | Raw history `[{year, pm25}, ...]`             |

---

## Health Impact Engine (IER/PAF)

**Files:** `health_engine.py` → `HealthRiskEngine`, `executive/predict_health.py`

### GBD 2019 Integrated Exposure-Response (IER) Model

The health engine computes **attributable deaths** using the Global Burden of Disease methodology:

#### Formula

```
exposure = max(0, PM2.5 - TMREL)     where TMREL = 5.0 µg/m³
RR(disease) = 1 + α × (1 - exp(-γ × exposure^δ))
PAF = (RR - 1) / RR
attributed_deaths = baseline_deaths × PAF
```

Where:
- **RR** = Relative Risk
- **PAF** = Population Attributable Fraction
- **α, γ, δ** = disease-specific parameters from GBD 2019

#### 10 Tracked Diseases

| Disease                         | Category       | α      | γ      |
|---------------------------------|----------------|--------|--------|
| Ischemic heart disease          | Cardiovascular | 0.2969 | 0.0133 |
| Stroke                          | Cardiovascular | 0.2794 | 0.0098 |
| COPD                            | Respiratory    | 0.2686 | 0.0160 |
| Lung cancer                     | Cancer         | 0.3195 | 0.0107 |
| Lower respiratory infections    | Respiratory    | 0.3624 | 0.0125 |
| Type 2 Diabetes                 | Metabolic      | 0.1850 | 0.0080 |
| Neonatal disorders              | Neonatal       | 0.2100 | 0.0095 |
| Preterm birth                   | Neonatal       | 0.1900 | 0.0088 |
| Low birth weight                | Neonatal       | 0.2050 | 0.0092 |
| Asthma                          | Respiratory    | 0.2350 | 0.0110 |

#### Age Vulnerability Multipliers

| Group               | Age Range | Multiplier |
|----------------------|-----------|------------|
| Children             | 0–14      | 1.3×       |
| Adults               | 15–64     | 1.0×       |
| Elderly              | 65+       | 1.5×       |

#### Confidence Intervals

95% CI bounds are computed as ±20% of the central death estimate.

### Key Functions

| Function                              | Returns                                |
|---------------------------------------|----------------------------------------|
| `predict_deaths(c, yr, pm25)`         | `(total_deaths, rate_per_100k)`        |
| `predict_attributable_deaths(c, yr)`  | Full dict: deaths, CI, disease list    |
| `predict_death_rate(c, yr)`           | Rate per 100,000 population proxy      |
| `top_diseases(c, yr, k=3)`           | Top-k diseases by attributed deaths    |
| `compare_health(cA, cB, yr)`         | Side-by-side country comparison        |

---

## Executive Analytics Layer

### Scenario Engine (`executive/scenario.py`)

What-if analysis: "What if PM2.5 drops 15%?"

```
1. baseline_pm25 = forecast(country, year)
2. scenario_pm25 = baseline × (1 + percent_change/100), clamped ≥ TMREL
3. baseline_deaths = health_engine(baseline_pm25)
4. scenario_deaths = health_engine(scenario_pm25)
5. prevented_deaths = baseline_deaths - scenario_deaths
```

Returns: baseline vs scenario PM2.5, deaths, delta, top diseases.

### Trend Forecast (`executive/trend.py`)

Multi-year PM2.5 trajectory analysis:

```
1. Predict PM2.5 for each year in [start, end] window
2. direction = "Increasing" / "Decreasing" / "Stable" (±2% threshold)
3. stability = coefficient of variation (CV = std/mean × 100)
4. health_impact = qualitative health burden text
```

### Risk Scoring (`executive/risk.py`)

**Composite Risk Score formula:**

```
score = normalize(PM2.5, 5-100) × 0.60
      + normalize(YoY%, -20 to +20) × 0.25
      + normalize(CI_width, 0-30) × 0.15
```

**Risk tiers:**

| PM2.5 Range   | Tier          | Emoji |
|---------------|---------------|-------|
| < 12.0        | Low           | 🟢    |
| 12.0–35.5     | Moderate      | 🟡    |
| 35.5–55.5     | High          | 🟠    |
| > 55.5        | Very High     | 🔴    |

### New Analytics (`executive/analytics.py`)

| Function                    | Purpose                                                  |
|-----------------------------|----------------------------------------------------------|
| `rank_pm25()`               | Sort countries by PM2.5 concentration (not risk score)   |
| `rank_stability()`          | Sort by CV of multi-year PM2.5 predictions               |
| `fastest_improving()`       | Sort by % change (most negative = fastest improving)     |
| `lowest_health_burden()`    | Sort by deaths or DALYs (ascending)                      |
| `sensitivity_pm25_deaths()` | Deaths prevented per 1% PM2.5 reduction                  |
| `deaths_change_yoy()`       | Year-over-year attributed deaths comparison              |

### Explainability (`executive/explainability.py`)

Returns top 3 XGBoost feature importances + top 2 disease drivers:

**Pollution drivers** (from XGBoost model):
- Previous year PM2.5 level (`lag_1y`)
- Year-over-year change trajectory (`yoy_change`)
- 3-year moving average trend (`rolling_mean_3y`)

**Health drivers** (from IER disease breakdown):
- PM2.5 exposure above safe threshold
- Top diseases by attributed deaths

---

## Confidence & Uncertainty

**File:** `executive/uncertainty.py`

| Forecast Distance | Confidence | Score | Note                    |
|-------------------|------------|-------|-------------------------|
| ≤ 3 years ahead   | High       | 0.90  | Near-term forecast      |
| 4–7 years ahead   | Moderate   | 0.70  | Compounding uncertainty |
| 8–12 years ahead  | Low        | 0.50  | Indicative trend only   |
| > 12 years ahead  | Speculative| 0.30  | Very high uncertainty   |

PM2.5 confidence interval: `±(pm25 × (1 - score) × 0.5)` µg/m³

---

## Data Files

| File                      | Size    | Contents                                    |
|---------------------------|---------|---------------------------------------------|
| `data/pm25_history.json`  | 157 KB  | Annual PM2.5 for 257 countries (2000–2019)  |
| `data/ihme_baseline.json` | 1.8 MB  | GBD disease baselines by country/age        |
| `models/xgboost_*.pkl`    | —       | Trained XGBoost model (pickle)              |

---

## API Reference

### POST /api/chat
Main chat endpoint — natural language query processing.

**Request:**
```json
{ "message": "What if PM2.5 drops 15% in Thailand?" }
```

**Response:**
```json
{
  "intent": "SCENARIO_PM25_CHANGE",
  "answer": "Scenario: PM2.5 reduced by 15%\nCountry: Thailand\n...",
  "data": { ... structured result ... },
  "parsed": { "country": "Thailand", "year": 2026, "percent": 15.0, "percent_sign": -1 }
}
```

### POST /api/predict
Direct PM2.5 prediction (no NLP).

```json
{ "country": "Thailand", "target_year": 2027 }
```

### POST /api/health-risk
Direct health impact calculation.

```json
{ "country": "Thailand", "target_year": 2027 }
```

### GET /api/countries
Returns list of available countries.

### GET /debug
System debug info (model status, available countries).
