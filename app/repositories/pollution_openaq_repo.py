import re
from typing import Any
from app.core.mongo import get_openaq_collection


_COUNTRY_ALIASES = {
    "united states of america": "United States",
    "usa": "United States",
    "u.s.a.": "United States",
    "u.s.": "United States",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "hong kong sar": "Hong Kong",
    "hong kong, china": "Hong Kong",
}


def _normalize_country_name(value: str) -> str:
    base = " ".join(value.strip().lower().split())
    return _COUNTRY_ALIASES.get(base, value.strip())


def _build_filters(params: dict[str, Any]) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    year = params.get("year")
    if year is not None:
        filters["year"] = int(year)

    pollutant = params.get("pollutant")
    if pollutant:
        filters["pollutant"] = pollutant

    country_name = params.get("country_name")
    if country_name:
        normalized = _normalize_country_name(country_name)
        filters["country_name"] = {"$regex": f"^{re.escape(normalized)}$", "$options": "i"}

    return filters


def list_openaq(params: dict[str, Any], limit: int, metric: str):
    col = get_openaq_collection()
    filters = _build_filters(params)
    sort_field = metric if metric in {"value", "avg", "min", "max", "median"} else "value"
    cursor = col.find(
        filters,
        {
            "_id": 0,
            "location_name": 1,
            "pollutant": 1,
            "units": 1,
            "coverage_percent": 1,
            "latitude": 1,
            "longitude": 1,
            "country_name": 1,
            "country_code": 1,
            "year": 1,
            "value": 1,
            "min": 1,
            "max": 1,
            "median": 1,
            "avg": 1,
        },
    ).sort(sort_field, -1).limit(int(limit))
    items = list(cursor)
    total = col.count_documents(filters)
    return total, items


def country_coverage_avg(year: int, pollutant: str = "PM2.5", country_name: str | None = None):
    col = get_openaq_collection()
    match: dict[str, Any] = {
        "year": int(year),
        "coverage_percent": {"$gte": 50},
        "avg": {"$type": "number"},
    }
    if pollutant:
        match["pollutant"] = pollutant
    if country_name:
        match["country_name"] = {"$regex": f"^{re.escape(country_name)}$", "$options": "i"}

    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": "$country_name",
                "numerator": {"$sum": {"$multiply": ["$avg", "$coverage_percent"]}},
                "denominator": {"$sum": "$coverage_percent"},
                "count": {"$sum": 1},
            }
        },
        {
            "$project": {
                "_id": 0,
                "country": "$_id",
                "pollution_pm25": {
                    "$cond": [
                        {"$gt": ["$denominator", 0]},
                        {"$divide": ["$numerator", "$denominator"]},
                        None,
                    ]
                },
                "count": 1,
            }
        },
        {"$sort": {"country": 1}},
    ]
    return list(col.aggregate(pipeline))


def trend_by_year(
    year_from: int,
    year_to: int,
    pollutant: str | None = None,
    country_name: str | None = None,
    metric: str = "avg",
):
    col = get_openaq_collection()
    match: dict[str, Any] = {
        "year": {"$gte": int(year_from), "$lte": int(year_to)},
    }
    if pollutant:
        match["pollutant"] = pollutant
    if country_name:
        normalized = _normalize_country_name(country_name)
        match["country_name"] = {"$regex": f"^{re.escape(normalized)}$", "$options": "i"}
    metric_field = metric if metric in {"value", "avg", "min", "max", "median"} else "avg"
    match[metric_field] = {"$type": "number"}

    pipeline = [
        {"$match": match},
        {"$group": {"_id": "$year", "value": {"$avg": f"${metric_field}"}}},
        {"$project": {"_id": 0, "year": "$_id", "value": 1}},
        {"$sort": {"year": 1}},
    ]
    return list(col.aggregate(pipeline))
