from typing import Any
import re
from app.core.mongo import get_acag_collection
from app.core.country_normalize import exact_country_regex, country_aliases


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


def _metric_field(metric: str) -> str:
    key = (metric or "").strip().lower()
    if key not in _METRIC_FIELDS:
        raise ValueError("metric must be one of ['pop_weighted', 'geo_mean']")
    return _METRIC_FIELDS[key]


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
                    FIELD_REGION: {
                        "$regex": f"^{re.escape(candidate)}$",
                        "$options": "i",
                    }
                }
            )
    if not clauses:
        clauses.append({FIELD_REGION: exact_country_regex(names[0])})
    return clauses


def _convert_expr(expr) -> dict:
    return {"$convert": {"input": expr, "to": "double", "onError": None, "onNull": None}}


def _metric_value_expr(metric_field: str) -> dict:
    direct = _convert_expr(f"${metric_field}")
    object_value = {
        "$let": {
            "vars": {
                "field": f"${metric_field}",
                "pairs": {"$objectToArray": f"${metric_field}"},
            },
            "in": {
                "$ifNull": [
                    _convert_expr("$$field.value"),
                    {
                        "$ifNull": [
                            _convert_expr("$$field.Value"),
                            {
                                "$ifNull": [
                                    _convert_expr("$$field.mean"),
                                    {
                                        "$ifNull": [
                                            _convert_expr("$$field.Mean"),
                                            _convert_expr({"$arrayElemAt": ["$$pairs.v", 0]}),
                                        ]
                                    },
                                ]
                            },
                        ]
                    },
                ]
            },
        }
    }
    return {
        "$cond": [
            {"$eq": [{"$type": f"${metric_field}"}, "object"]},
            object_value,
            direct,
        ]
    }


def _population_value_expr() -> dict:
    return _convert_expr(f"${FIELD_POP_TOTAL}")


def _build_filters(params: dict[str, Any], metric: str) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    year = params.get("year")
    if year is not None:
        filters[FIELD_YEAR] = int(year)

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


def list_acag(params: dict[str, Any], limit: int, offset: int, metric: str):
    col = get_acag_collection()
    filters = _build_filters(params, metric)
    metric_field = _metric_field(metric)
    metric_expr = _metric_value_expr(metric_field)
    pipeline = [
        {"$match": filters},
        {"$addFields": {"metric_value": metric_expr}},
        {"$match": {"metric_value": {"$type": "number"}}},
        {"$sort": {"metric_value": -1}},
        {"$skip": int(offset)},
        {"$limit": int(limit)},
        {
            "$project": {
                "_id": 0,
                FIELD_REGION: 1,
                FIELD_YEAR: 1,
                FIELD_POP_WEIGHTED: 1,
                FIELD_GEO_MEAN: 1,
                FIELD_POP_COVERAGE: 1,
                FIELD_GEO_COVERAGE: 1,
                FIELD_POP_TOTAL: 1,
                "metric_value": 1,
            }
        },
    ]
    items = list(col.aggregate(pipeline))

    count_pipeline = [
        {"$match": filters},
        {"$addFields": {"metric_value": metric_expr}},
        {"$match": {"metric_value": {"$type": "number"}}},
        {"$count": "total"},
    ]
    count_res = list(col.aggregate(count_pipeline))
    total = int(count_res[0]["total"]) if count_res else 0
    return total, items


def country_summary(params: dict[str, Any], metric: str):
    col = get_acag_collection()
    filters = _build_filters(params, metric)
    metric_field = _metric_field(metric)
    metric_expr = _metric_value_expr(metric_field)
    pop_expr = _population_value_expr()

    pipeline = [
        {"$match": filters},
        {
            "$addFields": {
                "metric_value": metric_expr,
                "population_value": {"$ifNull": [pop_expr, 0]},
            }
        },
        {"$match": {"metric_value": {"$type": "number"}}},
        {
            "$group": {
                "_id": f"${FIELD_REGION}",
                "numerator": {
                    "$sum": {"$multiply": ["$metric_value", "$population_value"]}
                },
                "denominator": {"$sum": "$population_value"},
                "avg_value": {"$avg": "$metric_value"},
                "count": {"$sum": 1},
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
    col = get_acag_collection()
    metric_field = _metric_field(metric)
    metric_expr = _metric_value_expr(metric_field)
    pop_expr = _population_value_expr()
    match: dict[str, Any] = {
        FIELD_YEAR: {"$gte": int(year_from), "$lte": int(year_to)},
    }
    if country_name:
        match["$or"] = _build_country_or([country_name])

    pipeline = [
        {"$match": match},
        {
            "$addFields": {
                "metric_value": metric_expr,
                "population_value": {"$ifNull": [pop_expr, 0]},
            }
        },
        {"$match": {"metric_value": {"$type": "number"}}},
        {
            "$group": {
                "_id": f"${FIELD_YEAR}",
                "numerator": {
                    "$sum": {"$multiply": ["$metric_value", "$population_value"]}
                },
                "denominator": {"$sum": "$population_value"},
                "avg_value": {"$avg": "$metric_value"},
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
