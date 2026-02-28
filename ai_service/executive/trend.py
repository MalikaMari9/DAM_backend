"""Trend & direction forecast module.

Projects PM2.5 over a multi-year window and computes direction,
percentage change, volatility, and qualitative health-burden impact.
"""

import numpy as np
from .predict_pm25 import get_predictor


def trend_forecast(
    country: str,
    start: int = 2026,
    end: int = 2030,
) -> dict:
    """Compute multi-year trend analysis.

    Returns dict with: direction, arrow, pct_change, stability,
    health_impact, predictions.
    """
    pred = get_predictor()
    result = pred.predict_range(country, start, end)

    if result is None:
        raise ValueError(f"No data available for country: {country}")

    predictions = result["predictions"]  # {year: pm25}
    years = sorted(predictions.keys())
    values = [predictions[y] for y in years]

    if len(values) < 2:
        raise ValueError("Need at least 2 years for trend analysis")

    # ── Direction ───────────────────────────────────────────────────
    start_val = values[0]
    end_val = values[-1]
    pct_change = (end_val - start_val) / start_val * 100.0 if start_val > 0 else 0.0
    pct_change = round(pct_change, 1)

    if pct_change > 2.0:
        direction = "Increasing"
        arrow = "↑"
    elif pct_change < -2.0:
        direction = "Decreasing"
        arrow = "↓"
    else:
        direction = "Stable"
        arrow = "→"

    # ── Stability (coefficient of variation) ────────────────────────
    mean_val = float(np.mean(values))
    std_val = float(np.std(values, ddof=1)) if len(values) > 1 else 0
    cv = (std_val / mean_val * 100) if mean_val > 0 else 0

    if cv < 5:
        stability = "Stable trend pattern (low volatility)"
    else:
        stability = "Volatile trend pattern (high volatility)"

    # ── Health burden impact text ───────────────────────────────────
    health_impact = _health_impact_text(direction, abs(pct_change))

    return {
        "country": country,
        "start_year": start,
        "end_year": end,
        "direction": direction,
        "arrow": arrow,
        "pct_change": pct_change,
        "stability": stability,
        "health_impact": health_impact,
        "predictions": predictions,
        "window_years": len(years),
    }


def _health_impact_text(direction: str, magnitude: float) -> str:
    """Generate qualitative health-burden text based on trend."""
    if direction == "Decreasing":
        if magnitude > 10:
            return (
                "Significant pollution decline expected. "
                "Health burden projected to decrease noticeably, "
                "with fewer pollution-attributable deaths over the projection window."
            )
        else:
            return (
                "Gradual pollution decline expected. "
                "Modest improvement in health burden anticipated "
                "over the projection window."
            )
    elif direction == "Increasing":
        if magnitude > 10:
            return (
                "Substantial pollution increase projected. "
                "Health burden expected to rise significantly, with "
                "growing attributable mortality from cardiovascular "
                "and respiratory conditions."
            )
        else:
            return (
                "Slight pollution increase projected. "
                "Health burden may grow marginally; continued monitoring "
                "and mitigation recommended."
            )
    else:
        return (
            "Pollution levels projected to remain roughly stable. "
            "Health burden expected to hold near current levels "
            "barring major policy or environmental changes."
        )
