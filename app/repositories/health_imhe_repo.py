from typing import Any
from app.core.mongo import get_imhe_collection


def _build_filters(params: dict[str, Any]) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    excluded_ages = params.get("exclude_age_names")
    if excluded_ages:
        filters["age_name"] = {"$nin": list(excluded_ages)}
    for key in [
        "year",
        "location_id",
        "cause_id",
        "age_id",
        "sex_id",
        "measure_id",
        "metric_id",
    ]:
        value = params.get(key)
        if value is not None:
            filters[key] = value

    for key in [
        "measure_name",
        "metric_name",
        "cause_name",
        "age_name",
        "sex_name",
        "location_name",
    ]:
        value = params.get(key)
        if value:
            filters[key] = value

    contains_value = params.get("cause_name_contains")
    if contains_value:
        filters["cause_name"] = {"$regex": contains_value, "$options": "i"}
    return filters


def list_imhe(params: dict[str, Any], limit: int, offset: int):
    col = get_imhe_collection()
    filters = _build_filters(params)
    cursor = (
        col.find(filters, {"_id": 0})
        .skip(int(offset))
        .limit(int(limit))
    )
    items = list(cursor)
    total = col.count_documents(filters)
    return total, items


def list_locations(params: dict[str, Any]):
    col = get_imhe_collection()
    match = _build_filters(params)
    return sorted(col.distinct("location_name", match))


def summary():
    col = get_imhe_collection()
    total = col.estimated_document_count()
    agg = list(
        col.aggregate(
            [
                {
                    "$group": {
                        "_id": None,
                        "min_year": {"$min": "$year"},
                        "max_year": {"$max": "$year"},
                    }
                }
            ]
        )
    )
    if agg:
        return {
            "total_docs": total,
            "min_year": agg[0].get("min_year"),
            "max_year": agg[0].get("max_year"),
        }
    return {"total_docs": total, "min_year": None, "max_year": None}


def country_summary(params: dict[str, Any]):
    col = get_imhe_collection()
    filters = _build_filters(params)

    pipeline = [
        {"$match": filters},
        {
            "$group": {
                "_id": "$location_name",
                "value": {"$avg": "$val"},
                "count": {"$sum": 1},
            }
        },
        {"$project": {"_id": 0, "country": "$_id", "value": 1, "count": 1}},
        {"$sort": {"country": 1}},
    ]
    return list(col.aggregate(pipeline))


def list_ages(params: dict[str, Any]):
    col = get_imhe_collection()
    filters = _build_filters(params)
    pipeline = [
        {"$match": filters},
        {"$group": {"_id": {"age_id": "$age_id", "age_name": "$age_name"}}},
        {"$project": {"_id": 0, "age_id": "$_id.age_id", "age_name": "$_id.age_name"}},
        {"$sort": {"age_id": 1}},
    ]
    return list(col.aggregate(pipeline))


def list_sexes(params: dict[str, Any]):
    col = get_imhe_collection()
    filters = _build_filters(params)
    pipeline = [
        {"$match": filters},
        {"$group": {"_id": {"sex_id": "$sex_id", "sex_name": "$sex_name"}}},
        {"$project": {"_id": 0, "sex_id": "$_id.sex_id", "sex_name": "$_id.sex_name"}},
        {"$sort": {"sex_id": 1}},
    ]
    return list(col.aggregate(pipeline))


def list_causes(params: dict[str, Any]):
    col = get_imhe_collection()
    filters = _build_filters(params)
    pipeline = [
        {"$match": filters},
        {"$group": {"_id": {"cause_id": "$cause_id", "cause_name": "$cause_name"}}},
        {"$project": {"_id": 0, "cause_id": "$_id.cause_id", "cause_name": "$_id.cause_name"}},
        {"$sort": {"cause_name": 1}},
    ]
    return list(col.aggregate(pipeline))
