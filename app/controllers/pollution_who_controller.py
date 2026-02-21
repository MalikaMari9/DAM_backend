from typing import Any
from app.core.country_normalize import normalize_country_name
from app.repositories.pollution_who_repo import list_who, country_summary, trend_by_year


_METRIC_LABELS = {
    "pm25": "PM2.5",
    "pm10": "PM10",
    "no2": "NO2",
}


def _get_metric_label(metric: str) -> str:
    return _METRIC_LABELS.get(metric.strip().lower(), metric)


def list_who_items(filters: dict[str, Any], limit: int, offset: int, metric: str):
    total, items = list_who(filters, limit=limit, offset=offset, metric=metric)
    metric_field = f"{metric.strip().lower()}_concentration"
    label = _get_metric_label(metric)
    for item in items:
        value = item.get(metric_field)
        item["location_name"] = item.get("city") or item.get("location_name")
        item["pollutant"] = label
        item["units"] = "ug/m3"
        item["value"] = value
        item["metric"] = "value"
        item["metric_value"] = value
        item["country_code"] = item.get("iso3")
        if item.get("country_name"):
            item["country_name"] = normalize_country_name(item["country_name"])
        if metric.strip().lower() == "pm25":
            item["coverage_percent"] = item.get("pm25_tempcov")
        else:
            item["coverage_percent"] = None
    return total, items


def get_who_country_summary(filters: dict[str, Any], metric: str):
    rows = country_summary(filters, metric=metric)
    if not rows:
        return rows

    merged: dict[str, dict[str, Any]] = {}
    for row in rows:
        raw_country = row.get("country") or ""
        country = normalize_country_name(raw_country)
        numerator = row.get("_numerator")
        denominator = row.get("_denominator")
        avg_value = row.get("_avg_value")
        value = row.get("value")
        count = row.get("count", 0) or 0
        lat = row.get("latitude")
        lon = row.get("longitude")

        entry = merged.get(country)
        if entry is None:
            merged[country] = {
                "country": country,
                "value": value,
                "count": count,
                "latitude": lat,
                "longitude": lon,
                "_numerator": numerator,
                "_denominator": denominator,
                "_avg_value": avg_value,
            }
            continue

        entry["count"] = (entry.get("count") or 0) + count
        prev_denominator = entry.get("_denominator") or 0
        prev_numerator = entry.get("_numerator") or 0

        if denominator is not None:
            new_denominator = prev_denominator + (denominator or 0)
            new_numerator = prev_numerator + (numerator or 0)
            entry["_denominator"] = new_denominator
            entry["_numerator"] = new_numerator
        elif avg_value is not None:
            entry["_avg_value"] = (
                (entry.get("_avg_value") or 0) + avg_value
            ) / 2

        if entry.get("_denominator"):
            entry["value"] = entry["_numerator"] / entry["_denominator"]
        else:
            entry["value"] = entry.get("_avg_value", entry.get("value"))

        if lat is not None and lon is not None and denominator:
            if entry.get("latitude") is not None and prev_denominator:
                entry["latitude"] = (
                    entry["latitude"] * prev_denominator + lat * denominator
                ) / (prev_denominator + denominator)
                entry["longitude"] = (
                    entry["longitude"] * prev_denominator + lon * denominator
                ) / (prev_denominator + denominator)
            else:
                entry["latitude"] = lat
                entry["longitude"] = lon

    results = []
    for entry in merged.values():
        entry.pop("_numerator", None)
        entry.pop("_denominator", None)
        entry.pop("_avg_value", None)
        results.append(entry)

    return sorted(results, key=lambda item: item["country"])


def get_who_trend(
    year_from: int,
    year_to: int,
    metric: str,
    country_name: str | None,
):
    return trend_by_year(
        year_from=year_from,
        year_to=year_to,
        metric=metric,
        country_name=country_name,
    )
