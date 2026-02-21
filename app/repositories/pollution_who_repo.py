from typing import Any
import re
from app.core.mongo import get_who_collection
from app.core.country_normalize import exact_country_regex, country_aliases


_METRIC_FIELDS = {
    "pm25": "pm25_concentration",
    "pm10": "pm10_concentration",
    "no2": "no2_concentration",
}


def _metric_field(metric: str) -> str:
    key = (metric or "").strip().lower()
    if key not in _METRIC_FIELDS:
        raise ValueError("metric must be one of ['pm25', 'pm10', 'no2']")
    return _METRIC_FIELDS[key]


def _build_filters(params: dict[str, Any], metric: str) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    year = params.get("year")
    if year is not None:
        filters["year"] = int(year)

    metric_field = _metric_field(metric)
    filters[metric_field] = {"$type": "number"}

    country_names = params.get("country_names")
    if country_names:
        names = [name for name in country_names if isinstance(name, str) and name.strip()]
        if names:
            filters["$or"] = _build_country_or(names)
    else:
        country_name = params.get("country_name")
        if country_name:
            filters["$or"] = _build_country_or([country_name])

    return filters


def _build_country_or(names: list[str]) -> list[dict[str, dict[str, str]]]:
    seen: set[str] = set()
    clauses: list[dict[str, dict[str, str]]] = []
    for name in names:
        for candidate in country_aliases(name):
            key = candidate.lower()
            if key in seen:
                continue
            seen.add(key)
            clauses.append(
                {
                    "country_name": {
                        "$regex": f"^{re.escape(candidate)}$",
                        "$options": "i",
                    }
                }
            )
    if not clauses:
        clauses.append({"country_name": exact_country_regex(names[0])})
    return clauses


def list_who(params: dict[str, Any], limit: int, offset: int, metric: str):
    col = get_who_collection()
    filters = _build_filters(params, metric)
    metric_field = _metric_field(metric)
    cursor = col.find(
        filters,
        {
            "_id": 0,
            "who_region": 1,
            "iso3": 1,
            "country_name": 1,
            "city": 1,
            "year": 1,
            "pm25_concentration": 1,
            "pm10_concentration": 1,
            "no2_concentration": 1,
            "pm25_tempcov": 1,
            "population": 1,
            "latitude": 1,
            "longitude": 1,
        },
    ).sort(metric_field, -1).skip(int(offset)).limit(int(limit))
    items = list(cursor)
    total = col.count_documents(filters)
    return total, items


def country_summary(params: dict[str, Any], metric: str):
    col = get_who_collection()
    filters = _build_filters(params, metric)
    metric_field = _metric_field(metric)

    pipeline = [
        {"$match": filters},
        {
            "$group": {
                "_id": "$country_name",
                "numerator": {"$sum": {"$multiply": [f"${metric_field}", "$population"]}},
                "denominator": {"$sum": "$population"},
                "avg_value": {"$avg": f"${metric_field}"},
                "count": {"$sum": 1},
                "lat": {"$avg": "$latitude"},
                "lon": {"$avg": "$longitude"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "country": "$_id",
                "value": {
                    "$cond": [
                        {"$gt": ["$denominator", 0]},
                        {"$divide": ["$numerator", "$denominator"]},
                        "$avg_value",
                    ]
                },
                "count": 1,
                "latitude": "$lat",
                "longitude": "$lon",
                "_numerator": "$numerator",
                "_denominator": "$denominator",
                "_avg_value": "$avg_value",
            }
        },
        {"$sort": {"country": 1}},
    ]
    return list(col.aggregate(pipeline))


def trend_by_year(
    year_from: int,
    year_to: int,
    metric: str,
    country_name: str | None = None,
):
    col = get_who_collection()
    metric_field = _metric_field(metric)
    match: dict[str, Any] = {
        "year": {"$gte": int(year_from), "$lte": int(year_to)},
        metric_field: {"$type": "number"},
    }
    if country_name:
        match["$or"] = _build_country_or([country_name])

    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": "$year",
                "numerator": {"$sum": {"$multiply": [f"${metric_field}", "$population"]}},
                "denominator": {"$sum": "$population"},
                "avg_value": {"$avg": f"${metric_field}"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "year": "$_id",
                "value": {
                    "$cond": [
                        {"$gt": ["$denominator", 0]},
                        {"$divide": ["$numerator", "$denominator"]},
                        "$avg_value",
                    ]
                },
            }
        },
        {"$sort": {"year": 1}},
    ]
    return list(col.aggregate(pipeline))
