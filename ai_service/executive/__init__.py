"""Executive output inference package.

Wraps existing PM25Predictor and HealthRiskEngine with add-on layers
for uncertainty, scenarios, explainability, risk, and trend analysis.
"""

from .predict_pm25 import (
    forecast_pm25,
    pm25_change_vs_last_year,
    pm25_change,
    get_pm25_history,
)
from .predict_health import (
    predict_deaths,
    predict_attributable_deaths,
    predict_death_rate,
    top_diseases,
    compare_health,
    deaths_change_vs_last_year,
    get_health_result,
)
from .uncertainty import pm25_uncertainty, health_uncertainty
from .scenario import simulate_pm25_change, simulate_pm25_reduction
from .explainability import drivers_pollution, drivers_health
from .risk import (
    risk_level,
    risk_health_summary,
    rank_countries_by_risk,
    highest_risk_country,
    compute_risk_score,
)
from .trend import trend_forecast
from .formatter import format_output
