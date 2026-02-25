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

# CORS â€” allow chat frontend from any origin
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

ihme_raw_path = os.getenv("AI_IHME_RAW_PATH")
default_raw = BASE / "data" / "health_ihme_clean.json"
if not ihme_raw_path and default_raw.exists():
    ihme_raw_path = str(default_raw)

health_engine = HealthRiskEngine(
    baseline_path=str(BASE / "data" / "ihme_baseline.json"),
    ihme_raw_path=ihme_raw_path,
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
    """Chat-style endpoint: parse natural language â†’ structured response.

    Your chat interface calls this with: {"message": "user's question"}
    Returns: structured JSON with 'answer' (human-readable) + full data.
    """
    parsed = query_parser.parse(req.message, history=req.messages)

    # --- List countries ---
    if parsed['intent'] == 'list_countries':
        countries = predictor.get_countries()
        names = [c['name'] for c in countries]
        return {
            'intent': 'list_countries',
            'answer': f"We have PM2.5 data for {len(names)} countries. Some examples: {', '.join(names[:10])}...",
            'data': {'countries': names, 'total': len(names)},
            'parsed': parsed,
        }

    # --- Need a country for all other intents ---
    country = parsed['country']
    if not country:
        return {
            'intent': parsed['intent'],
            'answer': "I couldn't identify a country in your question. Could you please specify a country? For example: 'What is the air quality in Myanmar for 2027?'",
            'error': 'no_country_found',
            'parsed': parsed,
        }

    year = parsed['year']
    month = parsed['month']
    age_group = parsed['age_group']
    disease = parsed['disease']

    # --- Best Month / Monthly Breakdown ---
    if parsed['intent'] == 'best_month' or (parsed['intent'] == 'predict_pm25_monthly' and month is None):
        monthly_data = _compute_all_months(country, year)
        if monthly_data is None:
            return _country_not_found(country, parsed)

        ranked = sorted(monthly_data, key=lambda m: m['pm25'])
        best = ranked[0]
        worst = ranked[-1]

        answer_fallback = (
            f"ðŸŒ **Best time to visit {country} in {year}** (based on air quality):\n\n"
            f"âœ… **Best month: {best['month_name']}** â€” PM2.5: {best['pm25']} Âµg/mÂ³ ({best['aqi']})\n"
            f"âŒ Worst month: {worst['month_name']} â€” PM2.5: {worst['pm25']} Âµg/mÂ³ ({worst['aqi']})\n\n"
            f"ðŸ† **Top 3 cleanest months:**\n"
        )
        for i, m in enumerate(ranked[:3], 1):
            answer_fallback += f"  {i}. {m['month_name']} â€” {m['pm25']} Âµg/mÂ³\n"

        answer_fallback += (
            f"\nðŸ’¡ The dry season (Novâ€“Mar) typically has higher pollution due to "
            f"agricultural burning and weather patterns. The rainy season (Junâ€“Sep) "
            f"tends to have cleaner air."
        )

        data_payload = {
            'country': country,
            'year': year,
            'best_month': best,
            'worst_month': worst,
            'all_months': ranked,
        }

        final_answer = llm_gen.generate_response(parsed['intent'], data_payload, req.message, answer_fallback)

        return {
            'intent': 'best_month',
            'answer': final_answer,
            'data': data_payload,
            'parsed': parsed,
        }

    # --- Worst Month ---
    if parsed['intent'] == 'worst_month':
        monthly_data = _compute_all_months(country, year)
        if monthly_data is None:
            return _country_not_found(country, parsed)

        ranked = sorted(monthly_data, key=lambda m: -m['pm25'])
        worst = ranked[0]

        answer_fallback = (
            f"âš ï¸ **Most polluted months in {country} ({year}):**\n\n"
        )
        for i, m in enumerate(ranked[:3], 1):
            answer_fallback += f"  {i}. {m['month_name']} â€” PM2.5: {m['pm25']} Âµg/mÂ³ ({m['aqi']})\n"

        answer_fallback += f"\nðŸ›¡ï¸ Consider wearing a mask outdoors during {ranked[0]['month_name']} and {ranked[1]['month_name']}."

        data_payload = {
            'country': country,
            'year': year,
            'worst_months': ranked[:3],
            'all_months': ranked,
        }
        
        final_answer = llm_gen.generate_response(parsed['intent'], data_payload, req.message, answer_fallback)

        return {
            'intent': 'worst_month',
            'answer': final_answer,
            'data': data_payload,
            'parsed': parsed,
        }

    # --- Comparison (Multi-country) ---
    if parsed['intent'] == 'comparison' or len(parsed['countries']) >= 2:
        countries = parsed['countries']
        if len(countries) < 2:
            return {
                'intent': 'comparison',
                'answer': "I see you want to compare, but I only found one country. Please specify two or more countries to compare. Example: 'Compare Myanmar and Thailand'",
                'parsed': parsed,
            }

        # Determine what to compare (Health vs PM2.5)
        is_health = any(kw in req.message.lower() for kw in ['health', 'death', 'mortality', 'risk', 'disease', 'stroke', 'cancer'])
        
        results = []
        for c in countries:
            pm25 = predictor.predict(c, year)
            if pm25:
                res = {'country': c, 'pm25': pm25['predicted_pm25']}
                if is_health:
                    risk = health_engine.calculate(c, pm25['predicted_pm25'], year)
                    res['deaths'] = risk.get('total_attributed_deaths', 0)
                    res['deaths_formatted'] = f"{res['deaths']:,.0f}"
                results.append(res)
        
        if not results:
            return _country_not_found(countries[0], parsed)

        # Build comparison answer fallback
        answer_fallback = f"ðŸ“Š **Comparison for {year}**:\n\n"
        if is_health:
            # Sort by deaths
            results = sorted(results, key=lambda x: x.get('deaths', 0), reverse=True)
            for r in results:
                answer_fallback += f"â€¢ **{r['country']}**: {r['deaths_formatted']} attributed deaths (PM2.5: {r['pm25']} Âµg/mÂ³)\n"
            
            if len(results) >= 2:
                diff = abs(results[0]['deaths'] - results[1]['deaths'])
                answer_fallback += f"\nDifference: {diff:,.0f} deaths between top two."
        else:
            # Sort by PM2.5
            results = sorted(results, key=lambda x: x['pm25'], reverse=True)
            for r in results:
                aqi = _aqi_label(r['pm25'])
                answer_fallback += f"â€¢ **{r['country']}**: {r['pm25']} Âµg/mÂ³ ({aqi})\n"

        final_answer = llm_gen.generate_response(parsed['intent'], {'comparison': results}, req.message, answer_fallback)

        return {
            'intent': 'comparison',
            'answer': final_answer,
            'data': results,
            'parsed': parsed,
        }

    # --- Trend (year-over-year) ---
    if parsed['intent'] == 'trend':
        range_result = predictor.predict_range(country, 2020, year)
        if range_result is None:
            return _country_not_found(country, parsed)

        preds = range_result['predictions']
        years_list = sorted(preds.keys())
        first_val = preds[years_list[0]]
        last_val = preds[years_list[-1]]
        change = last_val - first_val
        pct_change = (change / first_val * 100) if first_val > 0 else 0

        if change < -1:
            trend_word = "ðŸ“‰ **improving** (decreasing pollution)"
        elif change > 1:
            trend_word = "ðŸ“ˆ **worsening** (increasing pollution)"
        else:
            trend_word = "âž¡ï¸ **stable** (little change)"

        answer_fallback = (
            f"**PM2.5 trend for {country} ({years_list[0]}â€“{years_list[-1]}):**\n\n"
            f"Direction: {trend_word}\n"
            f"â€¢ {years_list[0]}: {first_val} Âµg/mÂ³\n"
            f"â€¢ {years_list[-1]}: {last_val} Âµg/mÂ³\n"
            f"â€¢ Change: {change:+.1f} Âµg/mÂ³ ({pct_change:+.1f}%)\n"
        )
        
        final_answer = llm_gen.generate_response(parsed['intent'], range_result, req.message, answer_fallback, req.messages)

        return {
            'intent': 'trend',
            'answer': final_answer,
            'data': range_result,
            'parsed': parsed,
        }

    # --- PM2.5 Prediction (with optional month) ---
    if parsed['intent'] in ('predict_pm25', 'predict_pm25_monthly'):
        if month:
            result = predictor.predict_monthly(country, year, month)
            if result is None:
                return _country_not_found(country, parsed)

            month_name = result['month_name']
            answer_fallback = (
                f"The predicted PM2.5 level for {country} in {month_name} {year} is "
                f"**{result['predicted_pm25']} Âµg/mÂ³** "
                f"(annual average: {result['annual_pm25']} Âµg/mÂ³, seasonal factor: {result['seasonal_factor']}x). "
                f"Confidence: {result['confidence']['level']}."
            )
            final_answer = llm_gen.generate_response(parsed['intent'], result, req.message, answer_fallback, req.messages)
            
            return {
                'intent': 'predict_pm25_monthly',
                'answer': final_answer,
                'data': result,
                'parsed': parsed,
            }
        else:
            result = predictor.predict(country, year)
            if result is None:
                return _country_not_found(country, parsed)

            answer_fallback = (
                f"The predicted annual PM2.5 level for {country} in {year} is "
                f"**{result['predicted_pm25']} Âµg/mÂ³**. "
                f"Confidence: {result['confidence']['level']}."
            )
            final_answer = llm_gen.generate_response(parsed['intent'], result, req.message, answer_fallback, req.messages)
            
            return {
                'intent': 'predict_pm25',
                'answer': final_answer,
                'data': result,
                'parsed': parsed,
            }

    # --- Health Risk ---
    if parsed['intent'] == 'health_risk':
        pm25_result = predictor.predict(country, year)
        if pm25_result is None:
            return _country_not_found(country, parsed)

        pm25_level = pm25_result['predicted_pm25']

        if age_group or disease:
            risk = health_engine.calculate_filtered(
                country, pm25_level, year,
                age_group=age_group,
                disease_filter=disease,
            )
        else:
            risk = health_engine.calculate(country, pm25_level, year)

        risk['pm25_forecast'] = pm25_result

        # Build human-readable answer
        answer_parts = [
            f"Health risk analysis for {country} in {year} "
            f"(PM2.5: {pm25_level} Âµg/mÂ³, AQI: {risk.get('aqi_category', {}).get('level', 'N/A')}):"
        ]

        if age_group and risk.get('filtered_deaths') is not None:
            age_label = risk['age_groups'][0]['age_group'] if risk.get('age_groups') else age_group
            answer_parts.append(
                f"\n\nFor **{age_label}**: approximately **{risk['filtered_deaths']:,.0f}** "
                f"attributable deaths (95% CI: {risk.get('filtered_ci_lower', 0):,.0f}â€“{risk.get('filtered_ci_upper', 0):,.0f})."
            )
        else:
            answer_parts.append(
                f"\n\nTotal attributable deaths: **{risk.get('total_attributed_deaths', 0):,.0f}** "
                f"(95% CI: {risk.get('total_ci_lower', 0):,.0f}â€“{risk.get('total_ci_upper', 0):,.0f})."
            )

        # Top diseases
        top_diseases = risk.get('diseases', [])[:3]
        if top_diseases:
            disease_lines = []
            for d in top_diseases:
                disease_lines.append(f"  â€¢ {d['disease']}: {d['attributed_deaths']:,.0f} deaths")
            answer_parts.append("\n\nTop diseases:\n" + "\n".join(disease_lines))

        answer_fallback = "".join(answer_parts)
        
        final_answer = llm_gen.generate_response(parsed['intent'], risk, req.message, answer_fallback, req.messages)

        return {
            'intent': 'health_risk',
            'answer': final_answer,
            'data': risk,
            'parsed': parsed,
        }

    # --- Fallback ---
    return {
        'intent': 'unknown',
        'answer': (
            "I can help with:\n"
            "â€¢ PM2.5 predictions: 'What is the air quality in Myanmar in 2030?'\n"
            "â€¢ Monthly forecasts: 'PM2.5 level in Thailand for April 2027'\n"
            "â€¢ Travel advice: 'What is the best month to travel to Myanmar in 2026?'\n"
            "â€¢ Pollution trends: 'Is air quality in India improving?'\n"
            "â€¢ Health risks: 'Health impact of pollution in India 2028'\n"
            "â€¢ Age-specific risks: 'How does pollution affect children in Myanmar?'\n"
            "â€¢ Country list: 'Which countries do you have data for?'"
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
    print("\n  [INFO] Air Quality & Health Risk Web App v3.0")
    print("  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•")
    print("  Dashboard:   http://localhost:9000")
    print("  API Docs:    http://localhost:9000/docs")
    print("  Chat API:    POST http://localhost:9000/api/chat")
    print("  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•\n")
    uvicorn.run(app, host="0.0.0.0", port=9000)

