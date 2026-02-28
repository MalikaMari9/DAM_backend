"""Risk-level classification module.

Maps PM2.5 concentration to a 4-tier risk scale with emoji indicators,
generates health-burden impact summaries, and supports multi-country ranking.
"""


# ── Risk thresholds (WHO / AQI-aligned) ─────────────────────────────

RISK_TIERS = [
    (12.0,  "🟢", "Low"),
    (35.5,  "🟡", "Moderate"),
    (55.5,  "🟠", "High"),
    (float("inf"), "🔴", "Very High"),
]

ASEAN_COUNTRIES = [
    "Brunei", "Cambodia", "Indonesia", "Laos", "Malaysia",
    "Myanmar", "Philippines", "Singapore", "Thailand", "Vietnam",
]


def risk_level(pm25_pred: float) -> tuple[str, str]:
    """Classify PM2.5 into a risk tier.

    Returns (emoji, text) — e.g. ("🟡", "Moderate").
    """
    for threshold, emoji, text in RISK_TIERS:
        if pm25_pred < threshold:
            return emoji, text
    return "🔴", "Very High"


def risk_health_summary(pm25_pred: float, deaths: float) -> str:
    """Generate a 1–2 sentence health-burden summary for the risk card."""
    _, level = risk_level(pm25_pred)

    if level == "Low":
        return (
            f"At {pm25_pred:.1f} µg/m³, air quality meets WHO interim targets. "
            f"Estimated ~{deaths:,.0f} pollution-attributed deaths — relatively low burden."
        )
    elif level == "Moderate":
        return (
            f"PM2.5 of {pm25_pred:.1f} µg/m³ poses moderate health risks, "
            f"contributing to an estimated ~{deaths:,.0f} attributed deaths annually. "
            f"Vulnerable groups (children, elderly) face elevated respiratory risk."
        )
    elif level == "High":
        return (
            f"At {pm25_pred:.1f} µg/m³, pollution significantly raises disease risk. "
            f"An estimated ~{deaths:,.0f} deaths are attributable to air pollution, "
            f"with cardiovascular and respiratory conditions most affected."
        )
    else:  # Very High
        return (
            f"PM2.5 of {pm25_pred:.1f} µg/m³ presents severe health hazards. "
            f"An estimated ~{deaths:,.0f} deaths are linked to air pollution exposure, "
            f"demanding urgent public health intervention."
        )


# ── Composite risk scoring ──────────────────────────────────────────

def _normalize(value: float, low: float, high: float) -> float:
    """Normalize value to 0–100 range."""
    if high <= low:
        return 50.0
    return max(0.0, min(100.0, (value - low) / (high - low) * 100.0))


def compute_risk_score(pm25: float, yoy_pct: float, interval: float) -> float:
    """Composite risk score (0–100).

    Formula: norm(pm25)*0.6 + norm(yoy_pct)*0.25 + norm(interval)*0.15
    """
    # PM2.5 range: 5–100 µg/m³ (typical for countries)
    n_pm25 = _normalize(pm25, 5.0, 100.0)
    # YoY change: -20% to +20%
    n_yoy = _normalize(yoy_pct, -20.0, 20.0)
    # Interval width: 0–30 µg/m³
    n_int = _normalize(interval, 0.0, 30.0)

    score = n_pm25 * 0.6 + n_yoy * 0.25 + n_int * 0.15
    return round(score, 1)


def rank_countries_by_risk(
    year: int,
    region: str = "ASEAN",
    country_list: list[str] | None = None,
) -> list[dict]:
    """Rank countries by composite risk score.

    If country_list is provided, use it directly.
    Otherwise fall back to ASEAN_COUNTRIES.

    Returns list of dicts sorted by score descending:
    [{country, pm25, risk_score, emoji, risk_text, yoy_pct}, ...]
    """
    from .predict_pm25 import forecast_pm25, pm25_change_vs_last_year
    from .uncertainty import pm25_uncertainty

    if country_list is not None:
        countries = country_list
    elif region == "ASEAN":
        countries = ASEAN_COUNTRIES
    else:
        countries = ASEAN_COUNTRIES  # fallback

    results = []
    for c in countries:
        try:
            pm25 = forecast_pm25(c, year)
            yoy, arrow = pm25_change_vs_last_year(c, year, pm25)
            interval, label = pm25_uncertainty(c, year, pm25)
            score = compute_risk_score(pm25, yoy, interval)
            emoji, text = risk_level(pm25)

            results.append({
                "country": c,
                "pm25": round(pm25, 2),
                "risk_score": score,
                "emoji": emoji,
                "risk_text": text,
                "yoy_pct": yoy,
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["risk_score"], reverse=True)
    return results


def highest_risk_country(
    year: int,
    region: str = "ASEAN",
    country_list: list[str] | None = None,
) -> dict:
    """Return the single highest-risk country."""
    ranked = rank_countries_by_risk(year, region, country_list=country_list)
    if not ranked:
        return {"country": "Unknown", "risk_score": 0, "pm25": 0}
    return ranked[0]
