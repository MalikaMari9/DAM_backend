"""Explainability / main-drivers engine.

Provides human-readable driver explanations for both pollution and
health predictions using XGBoost feature importances and IER disease
breakdown respectively.
"""

from .predict_pm25 import get_predictor
from .predict_health import get_health_result

# Human-readable feature labels
FEATURE_LABELS = {
    "lag_1y": "Previous year PM2.5 level",
    "lag_3y": "PM2.5 level three years ago",
    "yoy_change": "Year-over-year change trajectory",
    "yoy_pct_change": "Year-over-year percentage change",
    "rolling_mean_3y": "3-year moving average trend",
    "rolling_mean_5y": "5-year moving average trend",
    "year": "Calendar year (temporal trend)",
}

FEATURE_NAMES = [
    "lag_1y", "lag_3y", "yoy_change",
    "yoy_pct_change", "rolling_mean_3y", "rolling_mean_5y", "year",
]


def drivers_pollution(country: str, year: int, features: dict | None = None) -> list[dict]:
    """Return top 2–3 human-readable pollution drivers.

    Returns list of dicts with {feature, importance}.
    """
    pred = get_predictor()
    model = pred.model

    # XGBoost / sklearn API: feature_importances_
    try:
        importances = model.feature_importances_
    except AttributeError:
        return [{"feature": "Model does not expose feature importances", "importance": 0.0}]

    # Rank features by importance
    ranked = sorted(
        zip(FEATURE_NAMES, importances),
        key=lambda x: x[1],
        reverse=True,
    )

    drivers: list[dict] = []
    for fname, imp in ranked[:3]:
        label = FEATURE_LABELS.get(fname, fname)
        drivers.append({
            "feature": label,
            "importance": round(float(imp), 4),
        })

    return drivers


def drivers_health(
    country: str,
    year: int,
    pm25_pred: float,
    deaths_pred: float | None = None,
) -> list[dict]:
    """Return top 2–3 human-readable health-impact drivers.

    Based on IER disease breakdown from the health engine.
    Returns list of dicts with {feature, importance} or {disease, deaths}.
    """
    result = get_health_result(country, year, pm25_pred)
    diseases = result.get("diseases", [])

    drivers: list[dict] = []

    # PM2.5 exposure context
    tmrel = 5.0
    excess = max(0, pm25_pred - tmrel)
    drivers.append({
        "disease": f"PM2.5 exposure ({excess:.1f} above safe threshold)",
        "deaths": round(pm25_pred, 1),
    })

    # Top diseases (already sorted by attributed_deaths descending)
    for d in diseases[:2]:
        name = d["disease"]
        deaths = d["attributed_deaths"]
        drivers.append({
            "disease": f"{name} ({d.get('category', '')})",
            "deaths": round(deaths, 0),
        })

    return drivers
