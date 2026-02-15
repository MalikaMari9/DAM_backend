from typing import Any
from app.repositories.pollution_openaq_repo import list_openaq


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
