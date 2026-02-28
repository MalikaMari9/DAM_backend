"""Analytics functions for new intents.

All functions reuse existing PM2.5 predictor and health engine —
no new models. They compute rankings, stability, sensitivity, and
year-over-year comparisons over arbitrary country lists.
"""

from __future__ import annotations

from .predict_pm25 import forecast_pm25, get_predictor
from .predict_health import predict_deaths, predict_attributable_deaths


# ═══════════════════════════════════════════════════════════════════
#  1) RANK_PM25 — sort countries by PM2.5 level (not risk score)
# ═══════════════════════════════════════════════════════════════════

def rank_pm25(
    countries: list[str],
    year: int,
    top_n: int | None = None,
    ascending: bool = False,
) -> list[dict]:
    """Rank countries by predicted PM2.5 concentration.

    ascending=False → highest PM2.5 first (most polluted).
    ascending=True  → lowest PM2.5 first (cleanest).
    """
    results = []
    for c in countries:
        try:
            pm25 = forecast_pm25(c, year)
            results.append({"country": c, "pm25": round(pm25, 2)})
        except Exception:
            continue

    results.sort(key=lambda x: x["pm25"], reverse=not ascending)
    if top_n:
        results = results[:top_n]
    return results


# ═══════════════════════════════════════════════════════════════════
#  2) STABILITY — rank by coefficient of variation (lowest = stable)
# ═══════════════════════════════════════════════════════════════════

def rank_stability(
    countries: list[str],
    start_year: int = 2020,
    end_year: int = 2030,
) -> list[dict]:
    """Rank countries by PM2.5 volatility (CV = std/mean × 100).

    Returns list sorted ascending — lowest CV = most stable.
    """
    import numpy as np

    pred = get_predictor()
    results = []
    for c in countries:
        try:
            r = pred.predict_range(c, start_year, end_year)
            if r is None:
                continue
            values = list(r["predictions"].values())
            if len(values) < 2:
                continue
            mean_v = float(np.mean(values))
            std_v = float(np.std(values, ddof=1))
            cv = round((std_v / mean_v * 100) if mean_v > 0 else 0, 2)
            results.append({
                "country": c,
                "cv": cv,
                "mean_pm25": round(mean_v, 2),
                "std_pm25": round(std_v, 2),
                "label": "Stable" if cv < 5 else "Volatile",
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["cv"])
    return results


# ═══════════════════════════════════════════════════════════════════
#  3) FASTEST IMPROVEMENT — most negative % change over window
# ═══════════════════════════════════════════════════════════════════

def fastest_improving(
    countries: list[str],
    start_year: int = 2020,
    end_year: int = 2030,
) -> list[dict]:
    """Rank countries by PM2.5 % change (most negative first = improving).

    Returns list sorted ascending by pct_change.
    """
    pred = get_predictor()
    results = []
    for c in countries:
        try:
            r = pred.predict_range(c, start_year, end_year)
            if r is None:
                continue
            preds = r["predictions"]
            start_val = preds.get(start_year)
            end_val = preds.get(end_year)
            if start_val is None or end_val is None or start_val == 0:
                continue
            pct = round((end_val - start_val) / start_val * 100, 1)
            results.append({
                "country": c,
                "pm25_start": round(start_val, 2),
                "pm25_end": round(end_val, 2),
                "pct_change": pct,
                "direction": "Improving" if pct < 0 else "Worsening",
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["pct_change"])  # most negative first
    return results


# ═══════════════════════════════════════════════════════════════════
#  4) LOWEST HEALTH BURDEN — sort by deaths ascending
# ═══════════════════════════════════════════════════════════════════

def lowest_health_burden(
    countries: list[str],
    year: int,
    metric: str = "deaths",
) -> list[dict]:
    """Rank countries by health burden (lowest first).

    metric: "deaths" or "dalys" (DALYs approximated as deaths × 12.5).
    """
    results = []
    for c in countries:
        try:
            pm25 = forecast_pm25(c, year)
            deaths, rate = predict_deaths(c, year, pm25)
            if deaths <= 0:
                continue  # skip missing data
            value = deaths
            if metric.lower() == "dalys":
                value = deaths * 12.5  # WHO DALY approximation

            results.append({
                "country": c,
                "pm25": round(pm25, 2),
                "deaths": round(deaths, 0),
                "value": round(value, 0),
                "metric": metric.upper(),
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["value"])  # lowest first
    return results


# ═══════════════════════════════════════════════════════════════════
#  5) SENSITIVITY — deaths prevented per 1% PM2.5 reduction
# ═══════════════════════════════════════════════════════════════════

def sensitivity_pm25_deaths(
    countries: list[str],
    year: int,
    delta_percent: float = -5.0,
) -> dict:
    """Compute sensitivity of deaths to PM2.5 changes across countries.

    Returns:
        per_country: list of {country, baseline_deaths, scenario_deaths,
                              delta, prevented_per_1pct}
        avg_prevented_per_1pct: average across all countries
        top_sensitive: top 3 most sensitive countries
    """
    per_country = []
    abs_delta = abs(delta_percent)

    for c in countries:
        try:
            pm25_base = forecast_pm25(c, year)
            pm25_scen = max(pm25_base * (1 + delta_percent / 100), 5.0)
            base_deaths, _ = predict_deaths(c, year, pm25_base)
            scen_deaths, _ = predict_deaths(c, year, pm25_scen)

            if base_deaths <= 0:
                continue

            delta = base_deaths - scen_deaths  # positive = lives saved
            per_1pct = round(delta / abs_delta, 1) if abs_delta > 0 else 0

            per_country.append({
                "country": c,
                "pm25_baseline": round(pm25_base, 2),
                "baseline_deaths": round(base_deaths, 0),
                "scenario_deaths": round(scen_deaths, 0),
                "prevented": round(delta, 0),
                "prevented_per_1pct": per_1pct,
            })
        except Exception:
            continue

    per_country.sort(key=lambda x: x["prevented_per_1pct"], reverse=True)

    all_per_1 = [r["prevented_per_1pct"] for r in per_country]
    avg = round(sum(all_per_1) / len(all_per_1), 1) if all_per_1 else 0

    return {
        "year": year,
        "delta_percent": delta_percent,
        "per_country": per_country,
        "avg_prevented_per_1pct": avg,
        "top_sensitive": per_country[:3],
    }


# ═══════════════════════════════════════════════════════════════════
#  6) DEATHS CHANGE YoY — deaths(year) vs deaths(year-1)
# ═══════════════════════════════════════════════════════════════════

def deaths_change_yoy(country: str, year: int) -> dict:
    """Compute year-over-year change in attributable deaths.

    Falls back to nearest prior year if year-1 data missing.
    Returns dict with current/previous deaths, delta, and pct_change.
    """
    pm25_curr = forecast_pm25(country, year)
    deaths_curr, _ = predict_deaths(country, year, pm25_curr)

    # Try year-1 first, then search backward
    prev_year = year - 1
    deaths_prev = 0
    for y in range(prev_year, prev_year - 5, -1):
        try:
            pm25_prev = forecast_pm25(country, y)
            d, _ = predict_deaths(country, y, pm25_prev)
            if d > 0:
                deaths_prev = d
                prev_year = y
                break
        except Exception:
            continue

    if deaths_prev == 0:
        return {
            "country": country,
            "year": year,
            "deaths_current": round(deaths_curr, 0),
            "deaths_previous": None,
            "prev_year": None,
            "delta": None,
            "pct_change": None,
            "error": "No previous-year health data available for comparison",
        }

    delta = deaths_curr - deaths_prev
    pct = round(delta / deaths_prev * 100, 1) if deaths_prev > 0 else 0

    return {
        "country": country,
        "year": year,
        "prev_year": prev_year,
        "deaths_current": round(deaths_curr, 0),
        "deaths_previous": round(deaths_prev, 0),
        "delta": round(delta, 0),
        "pct_change": pct,
        "direction": "Increased" if delta > 0 else ("Decreased" if delta < 0 else "Unchanged"),
    }
