"""FastAPI web app for PM2.5 prediction and health risk analysis.

Includes:
- Original endpoints: /api/predict, /api/health-risk, /api/countries
- New endpoints: /api/chat, /api/monthly-predict, /api/health-risk-filtered
"""

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import os

try:
    from .inference import PM25Predictor
    from .health_engine import HealthRiskEngine
    from .query_parser import QueryParser
    from .llm_generator import OllamaGenerator
except ImportError:
    from inference import PM25Predictor
    from health_engine import HealthRiskEngine
    from query_parser import QueryParser
    from llm_generator import OllamaGenerator

# --- Setup ---
BASE = Path(__file__).resolve().parent
app = FastAPI(title="Air Quality & Health Risk API", version="3.0")

# CORS — allow chat frontend from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load engines at startup
predictor = PM25Predictor(
    model_path=str(BASE / "model" / "xgboost_v20260213_104212.pkl"),
    history_path=str(BASE / "data" / "pm25_history.json"),
)

health_engine = HealthRiskEngine(
    baseline_path=str(BASE / "data" / "ihme_baseline.json"),
    ihme_raw_path=(
        os.getenv("AI_IHME_RAW_PATH")
        or (
            str(BASE / "data" / "health_ihme_clean.json")
            if (BASE / "data" / "health_ihme_clean.json").exists()
            else (
                str(BASE.parent / "Pollution" / "health_ihme_clean.json")
                if (BASE.parent / "Pollution" / "health_ihme_clean.json").exists()
                else None
            )
        )
    ),
)

# Build query parser with available countries from both engines
all_countries = set(predictor.countries) | set(health_engine.get_available_countries())
query_parser = QueryParser(list(all_countries))

# Initialize LLM Generator
llm_gen = OllamaGenerator()

# Serve static files
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


# ========================
#  REQUEST MODELS
# ========================

class PredictRequest(BaseModel):
    country: str
    target_year: int = 2027

class MonthlyPredictRequest(BaseModel):
    country: str
    year: int = 2027
    month: int = 1

class HealthRiskRequest(BaseModel):
    country: str
    target_year: int = 2027

class HealthRiskFilteredRequest(BaseModel):
    country: str
    target_year: int = 2027
    age_group: Optional[str] = None   # children | adults | elderly
    disease: Optional[str] = None     # e.g. "stroke", "asthma"

class ChatRequest(BaseModel):
    message: str
    messages: Optional[list[dict[str, str]]] = None


# ========================
#  ORIGINAL ROUTES
# ========================

@app.get("/")
async def root():
    index_path = BASE / "static" / "index.html"
    if not index_path.exists():
        return {"error": f"FILE NOT FOUND: {index_path}"}
    return FileResponse(str(index_path))

@app.get("/debug")
async def debug_info():
    index_path = BASE / "static" / "index.html"
    return {
        "base_path": str(BASE),
        "static_exists": (BASE / "static").exists(),
        "index_exists": index_path.exists(),
        "index_path": str(index_path),
        "cwd": str(Path.cwd()),
        "files_in_static": [p.name for p in (BASE / "static").glob("*")] if (BASE / "static").exists() else []
    }

@app.get("/api/countries")
async def get_countries():
    countries = predictor.get_countries()
    return {"countries": countries, "total": len(countries)}

@app.post("/api/predict")
async def predict_pm25(req: PredictRequest):
    result = predictor.predict(req.country, req.target_year)
    if result is None:
        return {"error": f"Country '{req.country}' not found"}
    return result

@app.post("/api/health-risk")
async def health_risk(req: HealthRiskRequest):
    pm25_result = predictor.predict(req.country, req.target_year)
    if pm25_result is None:
        return {"error": f"Country '{req.country}' not found"}
    pm25_level = pm25_result['predicted_pm25']
    risk = health_engine.calculate(req.country, pm25_level, req.target_year)
    risk['pm25_forecast'] = pm25_result
    return risk


# ========================
#  NEW ENDPOINTS
# ========================

@app.post("/api/monthly-predict")
async def monthly_predict(req: MonthlyPredictRequest):
    """Predict PM2.5 for a specific month (applies seasonal factors)."""
    result = predictor.predict_monthly(req.country, req.year, req.month)
    if result is None:
        return {"error": f"Country '{req.country}' not found"}
    return result


@app.post("/api/health-risk-filtered")
async def health_risk_filtered(req: HealthRiskFilteredRequest):
    """Health risk with optional age group / disease filter."""
    pm25_result = predictor.predict(req.country, req.target_year)
    if pm25_result is None:
        return {"error": f"Country '{req.country}' not found"}

    pm25_level = pm25_result['predicted_pm25']
    risk = health_engine.calculate_filtered(
        req.country, pm25_level, req.target_year,
        age_group=req.age_group,
        disease_filter=req.disease,
    )
    risk['pm25_forecast'] = pm25_result
    return risk


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """Chat-style endpoint: parse natural language → structured response.

    Uses rule-based intent router and dispatches to executive/ functions
    with strict output templates.
    """
    from query_parser import COUNTRY_OPTIONAL_INTENTS

    parsed = query_parser.parse(req.message, history=req.messages)
    intent = parsed['intent']

    # --- List countries ---
    if intent == 'list_countries':
        countries = predictor.get_countries()
        names = [c['name'] for c in countries]
        return {
            'intent': 'list_countries',
            'answer': f"We have PM2.5 data for {len(names)} countries. Some examples: {', '.join(names[:10])}...",
            'data': {'countries': names, 'total': len(names)},
            'parsed': parsed,
        }

    # --- Need a country for most intents (but not ranking/highest) ---
    country = parsed['country']
    if not country and intent not in COUNTRY_OPTIONAL_INTENTS:
        return {
            'intent': intent,
            'answer': "I couldn't identify a country in your question. Could you please specify a country? For example: 'What is the air quality in Myanmar for 2027?'",
            'error': 'no_country_found',
            'parsed': parsed,
        }

    year = parsed['year']
    region = parsed.get('region')  # may be None, ASEAN, Europe, etc.

    # ── Dynamic region resolution ──
    from region_resolver import resolve_region_countries
    region_result = resolve_region_countries(region)
    region_countries = region_result["countries"]  # may be empty
    resolved_region = region_result["region"]      # canonical name

    if not region_result["ok"]:
        return {
            'intent': intent,
            'answer': region_result["error"],
            'error': 'unsupported_region',
            'parsed': parsed,
        }

    # Default region label for display
    if region is None:
        region = "Global"
        # region_countries already contains ALL dataset countries from resolve_region_countries(None)

    # ── Bug B: default country for country-optional intents ──
    if not country and intent in COUNTRY_OPTIONAL_INTENTS:
        if intent in ("SCENARIO_PM25_CHANGE", "EXPLAINABILITY", "HEALTH_DALYS"):
            country = "Myanmar"  # default scope
            parsed['country'] = country

    # ── Import executive modules lazily ──
    from executive.predict_pm25 import forecast_pm25 as exec_forecast, pm25_change_vs_last_year, pm25_change
    from executive.predict_health import (
        predict_attributable_deaths, predict_death_rate,
        top_diseases as exec_top_diseases, compare_health as exec_compare,
        predict_deaths as exec_predict_deaths,
    )
    from executive.uncertainty import pm25_uncertainty
    from executive.scenario import simulate_pm25_change
    from executive.trend import trend_forecast
    from executive.risk import (
        risk_level as exec_risk_level, risk_health_summary,
        rank_countries_by_risk, highest_risk_country,
    )
    from executive.explainability import drivers_pollution, drivers_health
    from executive.analytics import (
        rank_pm25 as exec_rank_pm25,
        rank_stability as exec_rank_stability,
        fastest_improving as exec_fastest_improving,
        lowest_health_burden as exec_lowest_health_burden,
        sensitivity_pm25_deaths as exec_sensitivity,
        deaths_change_yoy as exec_deaths_yoy,
    )
    from executive.formatter import format_output

    try:
        # ═════════════════════════════════════════════════════════
        #  SCENARIO_PM25_CHANGE (signed percent)
        # ═════════════════════════════════════════════════════════
        if intent == "SCENARIO_PM25_CHANGE":
            if not country:
                country = "Myanmar"  # fallback
            pct = parsed.get('percent') or 15.0
            sign = parsed.get('percent_sign', -1)
            percent_change = pct * sign  # e.g. +25 or -15

            result = simulate_pm25_change(country, year, percent_change)
            answer = format_output("scenario", result)

            return {
                'intent': intent,
                'answer': answer,
                'data': result,
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  SENSITIVITY_PM25_DEATHS
        # ═════════════════════════════════════════════════════════
        if intent == "SENSITIVITY_PM25_DEATHS":
            pct = parsed.get('percent') or 5.0
            result = exec_sensitivity(region_countries, year, delta_percent=-pct)
            result["region"] = region
            answer = format_output("sensitivity", result)
            return {
                'intent': intent,
                'answer': answer,
                'data': result,
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  LOWEST_HEALTH_BURDEN
        # ═════════════════════════════════════════════════════════
        if intent == "LOWEST_HEALTH_BURDEN":
            metric = "dalys" if "daly" in parsed.get('raw', '').lower() else "deaths"
            rankings = exec_lowest_health_burden(region_countries, year, metric)
            payload = {"year": year, "region": region, "metric": metric, "rankings": rankings}
            answer = format_output("lowest_health_burden", payload)
            return {
                'intent': intent,
                'answer': answer,
                'data': payload,
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  FASTEST_IMPROVEMENT_PM25
        # ═════════════════════════════════════════════════════════
        if intent == "FASTEST_IMPROVEMENT_PM25":
            rankings = exec_fastest_improving(region_countries, start_year=2020, end_year=year)
            payload = {"start_year": 2020, "end_year": year, "region": region, "rankings": rankings}
            answer = format_output("fastest_improving", payload)
            return {
                'intent': intent,
                'answer': answer,
                'data': payload,
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  STABILITY_PM25
        # ═════════════════════════════════════════════════════════
        if intent == "STABILITY_PM25":
            rankings = exec_rank_stability(region_countries, start_year=2020, end_year=year)
            payload = {"start_year": 2020, "end_year": year, "region": region, "rankings": rankings}
            answer = format_output("stability", payload)
            return {
                'intent': intent,
                'answer': answer,
                'data': payload,
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  RANK_PM25 (by PM2.5 level, not risk score)
        # ═════════════════════════════════════════════════════════
        if intent == "RANK_PM25":
            import re as _re
            top_match = _re.search(r'\btop\s+(\d+)', parsed.get('raw', ''))
            top_n = int(top_match.group(1)) if top_match else None
            rankings = exec_rank_pm25(region_countries, year, top_n=top_n)
            payload = {"year": year, "region": region, "top_n": top_n, "rankings": rankings}
            answer = format_output("rank_pm25", payload)
            return {
                'intent': intent,
                'answer': answer,
                'data': payload,
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  DEATHS_CHANGE_YOY
        # ═════════════════════════════════════════════════════════
        if intent == "DEATHS_CHANGE_YOY":
            if not country:
                country = "Myanmar"
            result = exec_deaths_yoy(country, year)
            answer = format_output("deaths_yoy", result)
            return {
                'intent': intent,
                'answer': answer,
                'data': result,
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  RISK_RANKING
        # ═════════════════════════════════════════════════════════
        if intent == "RISK_RANKING":
            rankings = rank_countries_by_risk(year, region, country_list=region_countries)
            payload = {"year": year, "region": region, "rankings": rankings}
            answer = format_output("risk_ranking", payload)
            return {
                'intent': intent,
                'answer': answer,
                'data': payload,
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  HIGHEST_RISK_COUNTRY
        # ═════════════════════════════════════════════════════════
        if intent == "HIGHEST_RISK_COUNTRY":
            top = highest_risk_country(year, region, country_list=region_countries)
            payload = {"year": year, "region": region, "top": top}
            answer = format_output("highest_risk", payload)
            return {
                'intent': intent,
                'answer': answer,
                'data': payload,
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  HEALTH_DALYS (fallback to deaths)
        # ═════════════════════════════════════════════════════════
        if intent == "HEALTH_DALYS":
            if not country:
                country = "Myanmar"  # fallback
            result = predict_attributable_deaths(country, year)

            # Bug E: check for zero deaths
            if result.get('deaths', 0) == 0:
                return {
                    'intent': intent,
                    'answer': (
                        f"No health impact data is available for {country} in {year}.\n"
                        f"This may be due to missing baseline health data for this country.\n\n"
                        f"Try a different country, e.g.: 'What is the predicted DALYs due to PM2.5 in Myanmar?'"
                    ),
                    'error': 'no_health_data',
                    'parsed': parsed,
                }

            result["dalys_available"] = False
            answer = format_output("health_dalys", result)
            return {
                'intent': intent,
                'answer': answer,
                'data': result,
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  RISK_LEVEL (single country)
        # ═════════════════════════════════════════════════════════
        if intent == "RISK_LEVEL":
            pm25 = exec_forecast(country, year)
            deaths, _ = exec_predict_deaths(country, year, pm25)
            emoji, risk_text = exec_risk_level(pm25)
            summary = risk_health_summary(pm25, deaths)
            payload = {
                "country": country, "year": year, "pm25": pm25,
                "emoji": emoji, "risk_text": risk_text,
                "health_summary": summary,
            }
            answer = format_output("risk_level", payload)
            return {
                'intent': intent,
                'answer': answer,
                'data': payload,
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  EXPLAINABILITY
        # ═════════════════════════════════════════════════════════
        if intent == "EXPLAINABILITY":
            if not country:
                country = "Myanmar"  # fallback
            try:
                pm25 = exec_forecast(country, year)
                poll_drivers = drivers_pollution(country, year)
                try:
                    health_drv = drivers_health(country, year, pm25)
                except Exception:
                    health_drv = [{"disease": "Health driver data unavailable", "deaths": 0}]
                interval, conf_label = pm25_uncertainty(country, year, pm25)
                payload = {
                    "country": country, "year": year,
                    "pollution_drivers": poll_drivers,
                    "health_drivers": health_drv,
                    "confidence_note": f"{conf_label} (\u00b1{interval:.1f} \u00b5g/m\u00b3)",
                }
                answer = format_output("explainability", payload)
            except Exception as e:
                answer = f"Explainability analysis for {country} ({year}): partial failure — {e}"
                payload = {"country": country, "year": year, "error": str(e)}
            return {
                'intent': intent,
                'answer': answer,
                'data': payload,
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  COMPARE_HEALTH
        # ═════════════════════════════════════════════════════════
        if intent == "COMPARE_HEALTH":
            countries_list = parsed['countries']
            if len(countries_list) < 2:
                return {
                    'intent': intent,
                    'answer': "I need two countries to compare. Please specify like: 'Compare Myanmar and India for 2026'",
                    'parsed': parsed,
                }
            result = exec_compare(countries_list[0], countries_list[1], year)
            answer = format_output("compare_health", result)
            return {
                'intent': intent,
                'answer': answer,
                'data': result,
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  PM25_CHANGE
        # ═════════════════════════════════════════════════════════
        if intent == "PM25_CHANGE":
            yr = parsed.get('year_range')
            if yr:
                y1, y2 = yr
            else:
                y1, y2 = year - 1, year
            result = pm25_change(country, y1, y2)
            answer = format_output("pm25_change", result)
            return {
                'intent': intent,
                'answer': answer,
                'data': result,
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  HEALTH_RATE
        # ═════════════════════════════════════════════════════════
        if intent == "HEALTH_RATE":
            result = predict_death_rate(country, year)
            answer = format_output("health_rate", result)
            return {
                'intent': intent,
                'answer': answer,
                'data': result,
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  TOP_DISEASES
        # ═════════════════════════════════════════════════════════
        if intent == "TOP_DISEASES":
            diseases = exec_top_diseases(country, year, k=3)
            payload = {"country": country, "year": year, "diseases": diseases}
            answer = format_output("top_diseases", payload)
            return {
                'intent': intent,
                'answer': answer,
                'data': payload,
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  HEALTH_DEATHS
        # ═════════════════════════════════════════════════════════
        if intent == "HEALTH_DEATHS":
            result = predict_attributable_deaths(country, year)

            # Bug E: check for zero deaths (missing data)
            if result.get('deaths', 0) == 0:
                return {
                    'intent': intent,
                    'answer': (
                        f"No health impact data is available for {country} in {year}.\n"
                        f"This may be due to missing baseline health data for this country.\n\n"
                        f"Countries with available health data include: Myanmar, Thailand, "
                        f"Indonesia, Vietnam, Philippines, Malaysia, Cambodia, Laos."
                    ),
                    'error': 'no_health_data',
                    'parsed': parsed,
                }

            answer = format_output("health_deaths", result)
            return {
                'intent': intent,
                'answer': answer,
                'data': result,
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  TREND_PM25
        # ═════════════════════════════════════════════════════════
        if intent == "TREND_PM25":
            yr = parsed.get('year_range')
            if yr:
                start_y, end_y = yr
            else:
                start_y, end_y = 2020, year
            result = trend_forecast(country, start_y, end_y)
            answer = format_output("trend", result)
            return {
                'intent': intent,
                'answer': answer,
                'data': result,
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  BEST_MONTH / WORST_MONTH
        # ═════════════════════════════════════════════════════════
        if intent in ("BEST_MONTH", "WORST_MONTH"):
            monthly_data = _compute_all_months(country, year)
            if monthly_data is None:
                return _country_not_found(country, parsed)

            if intent == "BEST_MONTH":
                ranked = sorted(monthly_data, key=lambda m: m['pm25'])
                best = ranked[0]
                worst = ranked[-1]
                answer = (
                    f"Best time to visit {country} in {year} (based on air quality):\n\n"
                    f"Best month: {best['month_name']} \u2014 PM2.5: {best['pm25']} \u00b5g/m\u00b3 ({best['aqi']})\n"
                    f"Worst month: {worst['month_name']} \u2014 PM2.5: {worst['pm25']} \u00b5g/m\u00b3 ({worst['aqi']})\n\n"
                    f"Top 3 cleanest months:\n"
                )
                for i, m in enumerate(ranked[:3], 1):
                    answer += f"  {i}. {m['month_name']} \u2014 {m['pm25']} \u00b5g/m\u00b3\n"
            else:
                ranked = sorted(monthly_data, key=lambda m: -m['pm25'])
                answer = f"Most polluted months in {country} ({year}):\n\n"
                for i, m in enumerate(ranked[:3], 1):
                    answer += f"  {i}. {m['month_name']} \u2014 PM2.5: {m['pm25']} \u00b5g/m\u00b3 ({m['aqi']})\n"

            return {
                'intent': intent,
                'answer': answer,
                'data': {'months': ranked},
                'parsed': parsed,
            }

        # ═════════════════════════════════════════════════════════
        #  PM25_FORECAST_MONTHLY
        # ═════════════════════════════════════════════════════════
        if intent == "PM25_FORECAST_MONTHLY":
            month = parsed.get('month')
            if month:
                result = predictor.predict_monthly(country, year, month)
                if result is None:
                    return _country_not_found(country, parsed)
                answer = (
                    f"Country: {country}\n"
                    f"Month: {result['month_name']} {year}\n"
                    f"Predicted PM2.5: {result['predicted_pm25']:.2f} \u00b5g/m\u00b3\n"
                    f"Annual average: {result['annual_pm25']:.2f} \u00b5g/m\u00b3\n"
                    f"Seasonal factor: {result['seasonal_factor']}x\n"
                    f"Confidence: {result['confidence']['level']}"
                )
                return {
                    'intent': intent,
                    'answer': answer,
                    'data': result,
                    'parsed': parsed,
                }

        # ═════════════════════════════════════════════════════════
        #  PM25_FORECAST (default fallback)
        # ═════════════════════════════════════════════════════════
        pm25 = exec_forecast(country, year)
        pct_change, arrow = pm25_change_vs_last_year(country, year, pm25)
        interval, label = pm25_uncertainty(country, year, pm25)

        payload = {
            "country": country, "year": year, "pm25": pm25,
            "pct_change": pct_change, "arrow": arrow,
            "interval": interval, "confidence_label": label,
        }
        answer = format_output("pollution_forecast", payload)

        return {
            'intent': 'PM25_FORECAST',
            'answer': answer,
            'data': payload,
            'parsed': parsed,
        }

    except Exception as e:
        return {
            'intent': intent,
            'answer': f"Error processing your request: {str(e)}",
            'error': str(e),
            'parsed': parsed,
        }

    # --- Fallback ---
    return {
        'intent': 'unknown',
        'answer': (
            "I can help with:\n"
            "\u2022 PM2.5 predictions: 'What is the air quality in Myanmar in 2030?'\n"
            "\u2022 Health deaths: 'How many deaths from pollution in Myanmar?'\n"
            "\u2022 Risk ranking: 'Show countries ranked by risk score in 2026'\n"
            "\u2022 Risk level: 'What is Myanmar's pollution risk level in 2026?'\n"
            "\u2022 Scenarios: 'What if PM2.5 reduces by 15% in India?'\n"
            "\u2022 DALYs: 'What is the predicted DALYs due to PM2.5 in Philippines?'\n"
            "\u2022 Compare: 'Compare Myanmar and India for 2026'\n"
            "\u2022 Trends: 'Is air quality in Thailand improving?'\n"
            "\u2022 Country list: 'Which countries do you have data for?'"
        ),
        'parsed': parsed,
    }



MONTH_NAMES_LIST = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]

def _compute_all_months(country: str, year: int):
    """Compute PM2.5 for all 12 months and return ranked list."""
    annual = predictor.predict(country, year)
    if annual is None:
        return None

    results = []
    for month in range(1, 13):
        monthly = predictor.predict_monthly(country, year, month)
        if monthly:
            results.append({
                'month': month,
                'month_name': MONTH_NAMES_LIST[month - 1],
                'pm25': monthly['predicted_pm25'],
                'aqi': _aqi_label(monthly['predicted_pm25']),
                'seasonal_factor': monthly['seasonal_factor'],
            })
    return results


def _aqi_label(pm25: float) -> str:
    """Return simple AQI category label."""
    if pm25 < 12:
        return 'Good'
    elif pm25 < 35.5:
        return 'Moderate'
    elif pm25 < 55.5:
        return 'Unhealthy for Sensitive Groups'
    elif pm25 < 150.5:
        return 'Unhealthy'
    elif pm25 < 250.5:
        return 'Very Unhealthy'
    else:
        return 'Hazardous'


def _country_not_found(country, parsed):
    return {
        'intent': parsed['intent'],
        'answer': f"Sorry, I don't have data for '{country}'. Try asking about another country.",
        'error': 'country_not_found',
        'parsed': parsed,
    }


if __name__ == "__main__":
    port = int(os.getenv("AI_SERVICE_PORT", "9010"))
    print("\n  [INFO] Air Quality & Health Risk Web App v3.0")
    print("  ==========================================")
    print(f"  Dashboard:   http://localhost:{port}")
    print(f"  API Docs:    http://localhost:{port}/docs")
    print(f"  Chat API:    POST http://localhost:{port}/api/chat")
    print("  ==========================================\n")
    uvicorn.run(app, host="0.0.0.0", port=port)
