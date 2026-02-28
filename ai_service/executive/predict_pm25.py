"""PM2.5 prediction wrapper — wraps existing PM25Predictor.

Adds year-over-year change calculations used by executive outputs.
"""

import json
import sys
import os
from pathlib import Path

# Ensure webapp/ is importable
_webapp_dir = str(Path(__file__).resolve().parent.parent)
if _webapp_dir not in sys.path:
    sys.path.insert(0, _webapp_dir)

from inference import PM25Predictor  # existing webapp/inference.py

# ── Singleton loader ────────────────────────────────────────────────
_predictor: PM25Predictor | None = None


def _get_predictor() -> PM25Predictor:
    """Lazy-load the PM25Predictor singleton."""
    global _predictor
    if _predictor is None:
        base = Path(__file__).resolve().parent.parent          # webapp/
        model_path = os.getenv("AI_PM25_MODEL_PATH") or str(
            base / "model" / "xgboost_v20260213_104212.pkl"
        )
        history_path = os.getenv("AI_PM25_HISTORY_PATH") or str(
            base / "data" / "pm25_history.json"
        )
        _predictor = PM25Predictor(model_path, history_path)
    return _predictor


def get_predictor() -> PM25Predictor:
    """Public access to the shared predictor instance."""
    return _get_predictor()


# ── Public API ──────────────────────────────────────────────────────

def forecast_pm25(country: str, year: int) -> float:
    """Return point PM2.5 prediction (µg/m³) for *country* in *year*.

    Uses recursive XGBoost forecasting under the hood.
    """
    pred = _get_predictor()
    result = pred.predict(country, year)
    if result is None:
        raise ValueError(f"No data available for country: {country}")
    return result["predicted_pm25"]


def pm25_change_vs_last_year(
    country: str, year: int, pm25_pred: float
) -> tuple[float, str]:
    """Compute % change vs previous year.

    Returns (pct_change, arrow) where arrow is ↑ / ↓ / →.
    """
    pred = _get_predictor()

    # Try to get previous-year value: prefer actuals, fall back to model
    prev_pm25 = _get_pm25_for_year(pred, country, year - 1)

    if prev_pm25 is None or prev_pm25 == 0:
        return 0.0, "→"

    pct = (pm25_pred - prev_pm25) / prev_pm25 * 100.0
    pct = round(pct, 1)

    if pct > 0.5:
        arrow = "↑"
    elif pct < -0.5:
        arrow = "↓"
    else:
        arrow = "→"

    return pct, arrow


def get_pm25_history(country: str) -> list[dict]:
    """Return raw history [{year, pm25}, …] for a country."""
    pred = _get_predictor()
    return list(pred.history.get(country, []))


def pm25_change(country: str, year1: int, year2: int) -> dict:
    """Compute PM2.5 change between two years.

    Uses actuals if available, forecast otherwise.

    Returns dict with: pm25_y1, pm25_y2, abs_change, pct_change, arrow.
    """
    pred = _get_predictor()
    pm25_y1 = _get_pm25_for_year(pred, country, year1)
    pm25_y2 = _get_pm25_for_year(pred, country, year2)

    if pm25_y1 is None:
        raise ValueError(f"No data for {country} in {year1}")
    if pm25_y2 is None:
        raise ValueError(f"No data for {country} in {year2}")

    abs_change = round(pm25_y2 - pm25_y1, 2)
    pct_change = round((pm25_y2 - pm25_y1) / pm25_y1 * 100, 1) if pm25_y1 > 0 else 0.0

    if pct_change > 0.5:
        arrow = "↑"
    elif pct_change < -0.5:
        arrow = "↓"
    else:
        arrow = "→"

    return {
        "country": country,
        "year1": year1,
        "year2": year2,
        "pm25_y1": round(pm25_y1, 2),
        "pm25_y2": round(pm25_y2, 2),
        "abs_change": abs_change,
        "pct_change": pct_change,
        "arrow": arrow,
    }


# ── Helpers ─────────────────────────────────────────────────────────

def _get_pm25_for_year(pred: PM25Predictor, country: str, year: int) -> float | None:
    """Get PM2.5 for a specific year — actual if available, else predicted."""
    history = pred.history.get(country, [])
    for h in history:
        if h["year"] == year:
            return h["pm25"]
    # Not in actuals → use model prediction
    result = pred.predict(country, year)
    if result and year in result.get("prediction_path", {}):
        return result["prediction_path"][year]
    return None
