"""Uncertainty & confidence engine (business-grade).

Computes prediction intervals from backtesting residuals (no retraining).
Maps interval width + forecast horizon → confidence labels.
"""

import numpy as np
from .predict_pm25 import get_predictor, get_pm25_history

# ── Constants ───────────────────────────────────────────────────────
LAST_KNOWN_YEAR = 2025          # latest year with actuals
HORIZON_GROWTH_RATE = 0.15      # uncertainty grows 15 % per extra year
BACKTEST_WINDOW = range(2020, 2025)  # years within recursive prediction range


# ── PM2.5 uncertainty ──────────────────────────────────────────────

def pm25_uncertainty(
    country: str, year: int, pm25_pred: float
) -> tuple[float, str]:
    """Compute prediction interval and confidence label.

    Returns (interval, confidence_label) where interval is the ± value
    in µg/m³ and label is "High" / "Medium" / "Low".
    """
    residuals = _collect_residuals(country)
    years_ahead = max(1, year - LAST_KNOWN_YEAR)

    if len(residuals) >= 2:
        std = float(np.std(residuals, ddof=1))
    else:
        # Fallback: use 15 % of predicted value as std estimate
        std = pm25_pred * 0.15

    # 95 % interval, widened by horizon
    interval = 1.96 * std * (1 + HORIZON_GROWTH_RATE * (years_ahead - 1))
    interval = round(max(interval, 0.5), 1)  # floor at 0.5 µg/m³

    label = _confidence_label(interval, years_ahead)
    return interval, label


def _collect_residuals(country: str) -> list[float]:
    """Backtest the model on known years and collect residuals.

    Uses the prediction_path from predict() which starts at 2020.
    Compares model's recursive forecast vs actuals for overlap years.
    """
    pred = get_predictor()
    history = get_pm25_history(country)
    actuals = {h["year"]: h["pm25"] for h in history}

    # Get prediction path up to latest backtest year
    max_bt_year = max(BACKTEST_WINDOW)
    try:
        result = pred.predict(country, max_bt_year)
    except Exception:
        return []

    if result is None:
        return []

    path = result.get("prediction_path", {})

    residuals: list[float] = []
    for yr in BACKTEST_WINDOW:
        if yr in actuals and yr in path:
            residuals.append(path[yr] - actuals[yr])

    return residuals


def _confidence_label(interval: float, years_ahead: int) -> str:
    """Map interval width + horizon to confidence tier."""
    if interval <= 3.0 and years_ahead <= 3:
        return "High"
    elif interval <= 6.0 and years_ahead <= 7:
        return "Medium"
    else:
        return "Low"


def confidence_note(label: str, years_ahead: int) -> str:
    """Return human-readable confidence note."""
    notes = {
        "High": "Near-term forecast with narrow error margin",
        "Medium": "Medium-range forecast; moderate uncertainty",
        "Low": "Long-range projection; treat as indicative",
    }
    note = notes.get(label, "")
    if years_ahead > 3:
        note += ". Confidence degrades for farther years"
    return note


# ── Health uncertainty ──────────────────────────────────────────────

def health_uncertainty(
    country: str, year: int, deaths_pred: float
) -> str:
    """Return confidence label for health-impact predictions.

    Health confidence is inherently lower than PM2.5 because it chains
    PM2.5 uncertainty through the non-linear IER curve + baseline
    mortality estimates.
    """
    years_ahead = max(1, year - LAST_KNOWN_YEAR)

    if years_ahead <= 2:
        return "Medium"
    elif years_ahead <= 5:
        return "Low-Medium"
    else:
        return "Low"
