from typing import Any
from app.core.country_normalize import normalize_country_name
from app.repositories.pollution_acag_repo import list_acag, country_summary, trend_by_year


FIELD_REGION = "Region"
FIELD_YEAR = "Year"
FIELD_POP_WEIGHTED = "Population-Weighted PM2"
FIELD_GEO_MEAN = "Geographic-Mean PM2"
FIELD_POP_COVERAGE = "Population Coverage [%]"
FIELD_GEO_COVERAGE = "Geographic Coverage [%]"
FIELD_POP_TOTAL = "Total Population [million people]"

_METRIC_FIELDS = {
    "pop_weighted": FIELD_POP_WEIGHTED,
    "geo_mean": FIELD_GEO_MEAN,
}


def list_acag_items(filters: dict[str, Any], limit: int, offset: int, metric: str):
    total, items = list_acag(filters, limit=limit, offset=offset, metric=metric)
    for item in items:
        region = item.get(FIELD_REGION) or item.get("country_name")
        year = item.get(FIELD_YEAR) or item.get("year")
        value = item.get("metric_value")
        item["location_name"] = region
        item["country_name"] = normalize_country_name(region) if region else region
        item["pollutant"] = "PM2.5"
        item["units"] = "ug/m3"
        item["value"] = value
        item["metric"] = metric
        item["metric_value"] = value
        item["year"] = year
        item["coverage_percent"] = item.get(FIELD_POP_COVERAGE)
        item["geographic_coverage_percent"] = item.get(FIELD_GEO_COVERAGE)
        item["population_million"] = item.get(FIELD_POP_TOTAL)
    return total, items


def get_acag_country_summary(filters: dict[str, Any], metric: str):
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

        entry = merged.get(country)
        if entry is None:
            merged[country] = {
                "country": country,
                "value": value,
                "count": count,
                "_numerator": numerator,
                "_denominator": denominator,
                "_avg_value": avg_value,
            }
            continue

        entry["count"] = (entry.get("count") or 0) + count
        prev_denominator = entry.get("_denominator") or 0
        prev_numerator = entry.get("_numerator") or 0

        if denominator is not None:
            entry["_denominator"] = prev_denominator + (denominator or 0)
            entry["_numerator"] = prev_numerator + (numerator or 0)
        elif avg_value is not None:
            entry["_avg_value"] = (
                (entry.get("_avg_value") or 0) + avg_value
            ) / 2

        if entry.get("_denominator"):
            entry["value"] = entry["_numerator"] / entry["_denominator"]
        else:
            entry["value"] = entry.get("_avg_value", entry.get("value"))

    results = []
    for entry in merged.values():
        entry.pop("_numerator", None)
        entry.pop("_denominator", None)
        entry.pop("_avg_value", None)
        results.append(entry)

    return sorted(results, key=lambda item: item["country"])


def get_acag_trend(
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
