"""Scenario engine — what-if PM2.5 change analysis.

Handles both increase and decrease scenarios. Computes baseline vs
scenario deaths and the delta (prevented or additional deaths).
"""

from .predict_pm25 import forecast_pm25
from .predict_health import predict_deaths, get_health_result
from .uncertainty import health_uncertainty

TMREL = 5.0  # Theoretical minimum risk exposure level


def simulate_pm25_change(
    country: str,
    year: int = 2026,
    percent_change: float = -15.0,
) -> dict:
    """Simulate a PM2.5 change scenario (increase or decrease).

    Parameters
    ----------
    country : str   – Country name.
    year    : int   – Forecast year (default 2026).
    percent_change : float – Signed percent change.
        Negative = reduction (e.g. -15 means 15% decrease).
        Positive = increase (e.g. +25 means 25% increase).

    Returns
    -------
    dict with baseline/scenario pm25, deaths, delta, direction info.
    """
    # 1. Baseline prediction
    baseline_pm25 = forecast_pm25(country, year)

    # 2. Apply change, clamp to TMREL minimum
    scenario_pm25 = max(baseline_pm25 * (1 + percent_change / 100.0), TMREL)

    # 3. Deaths under each scenario
    baseline_deaths, baseline_rate = predict_deaths(country, year, baseline_pm25)
    scenario_deaths, scenario_rate = predict_deaths(country, year, scenario_pm25)

    # 4. Delta
    delta = scenario_deaths - baseline_deaths
    is_increase = percent_change > 0

    if is_increase:
        additional_deaths = max(0, delta)
        prevented_deaths = 0
    else:
        prevented_deaths = max(0, -delta)
        additional_deaths = 0

    # 5. Confidence
    conf = health_uncertainty(country, year, baseline_deaths)
    if conf == "High":
        conf = "Medium"

    # 6. Top diseases driving burden
    health_result = get_health_result(country, year, scenario_pm25)
    diseases = health_result.get("diseases", [])
    top_diseases = [d["disease"] for d in diseases[:3]]

    return {
        "country": country,
        "year": year,
        "percent_change": round(percent_change, 1),
        "is_increase": is_increase,
        "reduction_pct": round(abs(percent_change), 0),  # compat
        "baseline_pm25": round(baseline_pm25, 2),
        "scenario_pm25": round(scenario_pm25, 2),
        "baseline_deaths": round(baseline_deaths, 0),
        "scenario_deaths": round(scenario_deaths, 0),
        "prevented_deaths": round(prevented_deaths, 0),
        "additional_deaths": round(additional_deaths, 0),
        "baseline_rate": round(baseline_rate, 1),
        "scenario_rate": round(scenario_rate, 1),
        "confidence": conf,
        "top_diseases": top_diseases,
    }


# Backward-compat alias
def simulate_pm25_reduction(
    country: str, year: int = 2026, reduction: float = 0.15,
) -> dict:
    """Legacy wrapper — converts unsigned reduction to signed percent."""
    return simulate_pm25_change(country, year, percent_change=-reduction * 100)
