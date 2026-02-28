"""Health-impact prediction wrapper — wraps existing HealthRiskEngine.

Adds rate-per-100k computation and year-over-year death change.
"""

import os
import sys
from pathlib import Path

_webapp_dir = str(Path(__file__).resolve().parent.parent)
if _webapp_dir not in sys.path:
    sys.path.insert(0, _webapp_dir)

from health_engine import HealthRiskEngine  # existing webapp/health_engine.py
from .predict_pm25 import forecast_pm25

# ── Singleton loader ────────────────────────────────────────────────
_engine: HealthRiskEngine | None = None


def _get_engine() -> HealthRiskEngine:
    """Lazy-load the HealthRiskEngine singleton."""
    global _engine
    if _engine is None:
        base = Path(__file__).resolve().parent.parent  # webapp/
        ihme_raw_path = os.getenv("AI_IHME_RAW_PATH")
        if not ihme_raw_path:
            local_raw = base / "data" / "health_ihme_clean.json"
            legacy_raw = base.parent / "Pollution" / "health_ihme_clean.json"
            if local_raw.exists():
                ihme_raw_path = str(local_raw)
            elif legacy_raw.exists():
                ihme_raw_path = str(legacy_raw)
            else:
                ihme_raw_path = None

        _engine = HealthRiskEngine(
            baseline_path=(
                os.getenv("AI_IHME_BASELINE_PATH")
                or str(base / "data" / "ihme_baseline.json")
            ),
            ihme_raw_path=ihme_raw_path,
        )
    return _engine


def get_engine() -> HealthRiskEngine:
    """Public access to the shared health engine instance."""
    return _get_engine()


# ── Public API ──────────────────────────────────────────────────────

def predict_deaths(
    country: str, year: int, pm25_value: float
) -> tuple[float, float]:
    """Predict attributed deaths and rate per 100 000.

    Returns (total_attributed_deaths, rate_per_100k).
    """
    engine = _get_engine()
    result = engine.calculate(country, pm25_value, year)

    deaths = float(result.get("total_attributed_deaths", 0))

    # Compute rate per 100k using disease baselines as denominator proxy
    total_baseline = sum(
        d.get("baseline_deaths", 0) for d in result.get("diseases", [])
    )
    if total_baseline > 0:
        rate = deaths / total_baseline * 100_000
    else:
        rate = 0.0

    return round(deaths, 0), round(rate, 1)


def predict_attributable_deaths(
    country: str, year: int, pm25_value: float | None = None
) -> dict:
    """Full attributable-deaths result with CI bounds and disease breakdown.

    If pm25_value is None, forecast it first.
    Returns dict with: deaths, ci_low, ci_high, diseases, pm25.
    """
    if pm25_value is None:
        pm25_value = forecast_pm25(country, year)

    engine = _get_engine()
    result = engine.calculate(country, pm25_value, year)

    deaths = float(result.get("total_attributed_deaths", 0))
    ci_low = float(result.get("total_ci_lower", 0))
    ci_high = float(result.get("total_ci_upper", 0))

    diseases = []
    for d in result.get("diseases", []):
        diseases.append({
            "disease": d["disease"],
            "deaths": round(d["attributed_deaths"], 0),
            "category": d.get("category", ""),
        })

    return {
        "country": country,
        "year": year,
        "pm25": round(pm25_value, 2),
        "deaths": round(deaths, 0),
        "ci_low": round(ci_low, 0),
        "ci_high": round(ci_high, 0),
        "diseases": diseases,
    }


def predict_death_rate(
    country: str, year: int, deaths_total: float | None = None
) -> dict:
    """Compute pollution-related death rate per 100,000.

    Returns dict with: rate, deaths, population_proxy.
    """
    if deaths_total is None:
        pm25 = forecast_pm25(country, year)
        deaths_total, _ = predict_deaths(country, year, pm25)

    engine = _get_engine()
    pm25 = forecast_pm25(country, year)
    result = engine.calculate(country, pm25, year)

    # Use total baseline deaths as a population proxy
    # (real population data not available)
    total_baseline = sum(
        d.get("baseline_deaths", 0) for d in result.get("diseases", [])
    )

    if total_baseline > 0:
        rate = deaths_total / total_baseline * 100_000
    else:
        rate = 0.0

    return {
        "country": country,
        "year": year,
        "rate": round(rate, 1),
        "deaths": round(deaths_total, 0),
        "population_proxy": round(total_baseline, 0),
    }


def top_diseases(country: str, year: int, k: int = 3) -> list[dict]:
    """Return top-k diseases by attributed deaths.

    Returns list of dicts with: disease, deaths.
    """
    pm25 = forecast_pm25(country, year)
    engine = _get_engine()
    result = engine.calculate(country, pm25, year)

    diseases = result.get("diseases", [])
    # Already sorted by attributed_deaths descending
    return [
        {"disease": d["disease"], "deaths": round(d["attributed_deaths"], 0)}
        for d in diseases[:k]
    ]


def compare_health(countryA: str, countryB: str, year: int) -> dict:
    """Compare health impact between two countries.

    Returns dict with: countryA data, countryB data, difference.
    """
    pm25_a = forecast_pm25(countryA, year)
    pm25_b = forecast_pm25(countryB, year)
    deaths_a, _ = predict_deaths(countryA, year, pm25_a)
    deaths_b, _ = predict_deaths(countryB, year, pm25_b)

    diff = abs(deaths_a - deaths_b)

    return {
        "year": year,
        "countryA": countryA,
        "pm25A": round(pm25_a, 2),
        "deathsA": round(deaths_a, 0),
        "countryB": countryB,
        "pm25B": round(pm25_b, 2),
        "deathsB": round(deaths_b, 0),
        "diff": round(diff, 0),
    }


def deaths_change_vs_last_year(
    country: str, year: int, deaths_pred: float
) -> float:
    """Compute % change in attributed deaths vs previous year.

    Returns pct_change (positive = more deaths).
    """
    try:
        prev_pm25 = forecast_pm25(country, year - 1)
        prev_deaths, _ = predict_deaths(country, year - 1, prev_pm25)
    except Exception:
        return 0.0

    if prev_deaths == 0:
        return 0.0

    pct = (deaths_pred - prev_deaths) / prev_deaths * 100.0
    return round(pct, 1)


def get_health_result(country: str, year: int, pm25: float) -> dict:
    """Return the full health-engine result dict (for driver analysis)."""
    engine = _get_engine()
    return engine.calculate(country, pm25, year)
