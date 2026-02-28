"""Executive Report — orchestrates all five executive outputs.

Each generate_* function calls the relevant inference modules,
assembles a payload dict, and passes it through the formatter.

Run directly to see example outputs:
    cd "d:\\BreatheEasywithAImodel\\Pollution ETL\\AntiDev"
    python -m webapp.executive.executive_report
"""

from .predict_pm25 import forecast_pm25, pm25_change_vs_last_year
from .predict_health import predict_deaths, deaths_change_vs_last_year
from .uncertainty import pm25_uncertainty, health_uncertainty, confidence_note
from .scenario import simulate_pm25_reduction
from .explainability import drivers_pollution, drivers_health
from .risk import risk_level, risk_health_summary
from .trend import trend_forecast
from .formatter import format_output


# ═══════════════════════════════════════════════════════════════════
#  1. Country Pollution Forecast
# ═══════════════════════════════════════════════════════════════════

def generate_pollution_forecast(country: str, year: int) -> str:
    """Generate the Country Pollution Forecast executive output."""
    pm25 = forecast_pm25(country, year)
    pct_change, arrow = pm25_change_vs_last_year(country, year, pm25)
    interval, label = pm25_uncertainty(country, year, pm25)

    payload = {
        "country": country,
        "year": year,
        "pm25": pm25,
        "pct_change": pct_change,
        "arrow": arrow,
        "interval": interval,
        "confidence_label": label,
    }
    return format_output("pollution_forecast", payload)


# ═══════════════════════════════════════════════════════════════════
#  2. Health Impact Forecast
# ═══════════════════════════════════════════════════════════════════

def generate_health_impact(country: str, year: int) -> str:
    """Generate the Health Impact Forecast executive output."""
    pm25 = forecast_pm25(country, year)
    deaths, rate = predict_deaths(country, year, pm25)
    pct = deaths_change_vs_last_year(country, year, deaths)
    drivers = drivers_health(country, year, pm25, deaths)
    conf = health_uncertainty(country, year, deaths)

    payload = {
        "country": country,
        "year": year,
        "deaths": deaths,
        "rate": rate,
        "deaths_pct_change": pct,
        "drivers": drivers,
        "health_confidence": conf,
    }
    return format_output("health_impact", payload)


# ═══════════════════════════════════════════════════════════════════
#  3. Risk Level Classification
# ═══════════════════════════════════════════════════════════════════

def generate_risk_classification(country: str, year: int) -> str:
    """Generate the Risk Level Classification executive output."""
    pm25 = forecast_pm25(country, year)
    deaths, _ = predict_deaths(country, year, pm25)
    emoji, text = risk_level(pm25)
    summary = risk_health_summary(pm25, deaths)

    payload = {
        "country": country,
        "year": year,
        "pm25": pm25,
        "emoji": emoji,
        "risk_text": text,
        "health_summary": summary,
    }
    return format_output("risk_level", payload)


# ═══════════════════════════════════════════════════════════════════
#  4. Scenario Question
# ═══════════════════════════════════════════════════════════════════

def generate_scenario(
    country: str, year: int = 2026, reduction: float = 0.15
) -> str:
    """Generate the Scenario Question executive output."""
    result = simulate_pm25_reduction(country, year, reduction)
    return format_output("scenario", result)


# ═══════════════════════════════════════════════════════════════════
#  5. Trend & Direction Forecast
# ═══════════════════════════════════════════════════════════════════

def generate_trend(
    country: str, start: int = 2026, end: int = 2030
) -> str:
    """Generate the Trend & Direction Forecast executive output."""
    result = trend_forecast(country, start, end)
    return format_output("trend", result)


# ═══════════════════════════════════════════════════════════════════
#  Full Report (all 5 in one)
# ═══════════════════════════════════════════════════════════════════

def generate_full_report(country: str, year: int) -> str:
    """Generate all five executive outputs for a country/year."""
    sections = [
        generate_pollution_forecast(country, year),
        generate_health_impact(country, year),
        generate_risk_classification(country, year),
        generate_scenario(country, year, 0.15),
        generate_trend(country, year, year + 4),
    ]
    separator = "\n" + "=" * 60 + "\n\n"
    return separator.join(sections)


# ═══════════════════════════════════════════════════════════════════
#  Demo runner
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  EXECUTIVE OUTPUT DEMO")
    print("=" * 60)

    # ── Myanmar 2026 (full report) ──
    print("\n\n>>> Myanmar 2026 — Full Report\n")
    print(generate_full_report("Myanmar", 2026))

    # ── India 2026 with -15 % PM2.5 scenario ──
    print("\n\n>>> India 2026 — Scenario: PM2.5 reduced by 15%\n")
    print(generate_scenario("India", 2026, 0.15))

    # ── Thailand 2026-2030 trend ──
    print("\n\n>>> Thailand 2026–2030 — Trend Forecast\n")
    print(generate_trend("Thailand", 2026, 2030))

    print("\n" + "=" * 60)
    print("  DEMO COMPLETE")
    print("=" * 60)
