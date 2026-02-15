from typing import Any
from app.repositories.pollution_openaq_repo import (
    list_openaq,
    trend_by_year,
    list_distinct_pollutants,
    list_distinct_units,
    list_location_suggestions,
)


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


def list_openaq_items(filters: dict[str, Any], limit: int, offset: int, metric: str):
    total, items = list_openaq(filters, limit=limit, offset=offset, metric=metric)
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


def get_openaq_pollutants(country_name: str | None = None):
    return list_distinct_pollutants(country_name=country_name)


def get_openaq_units(country_name: str | None = None, pollutant: str | None = None):
    return list_distinct_units(country_name=country_name, pollutant=pollutant)


def get_openaq_locations(country_name: str | None, query: str | None, limit: int = 20):
    return list_location_suggestions(country_name=country_name, query=query, limit=limit)
