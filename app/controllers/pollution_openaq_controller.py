from typing import Any
from app.repositories.pollution_openaq_repo import list_openaq, trend_by_year


def _get_metric_value(item: dict, metric: str):
    if metric == "avg":
        return item.get("avg")
    if metric == "min":
        return item.get("min")
    if metric == "max":
        return item.get("max")
    if metric == "median":
        return item.get("median")
    return item.get("value")


def list_openaq_items(filters: dict[str, Any], limit: int, metric: str):
    total, items = list_openaq(filters, limit=limit, metric=metric)
    for item in items:
        item["metric"] = metric
        item["metric_value"] = _get_metric_value(item, metric)
    return total, items


def get_openaq_trend(
    year_from: int,
    year_to: int,
    pollutant: str | None,
    country_name: str | None,
    metric: str,
    method: str,
):
    return trend_by_year(
        year_from=year_from,
        year_to=year_to,
        pollutant=pollutant,
        country_name=country_name,
        metric=metric,
        method=method,
    )
