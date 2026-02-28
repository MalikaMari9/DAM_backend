from typing import Any, Literal
import os
import re

from app.core.mongo import get_acag_collection, get_acag_pred_collection
from app.core.country_normalize import (
    exact_country_regex,
    country_aliases,
    normalize_country_name,
)


FIELD_REGION = "Region"
FIELD_YEAR = "Year"
FIELD_POP_WEIGHTED = "Population-Weighted PM2"
FIELD_GEO_MEAN = "Geographic-Mean PM2"
FIELD_POP_COVERAGE = "Population Coverage [%]"
FIELD_GEO_COVERAGE = "Geographic Coverage [%]"
FIELD_POP_TOTAL = "Total Population [million people]"

PRED_FIELD_REGION = "region"
PRED_FIELD_SOURCE_REGION = "source_region"
PRED_FIELD_COUNTRY_KEY = "country_key"
PRED_FIELD_YEAR = "year"
PRED_FIELD_POP_WEIGHTED = "population_weighted_pm25_ugm3"
PRED_FIELD_GEO_MEAN = "geographic_mean_pm25_ugm3"
PRED_FIELD_POP_COVERAGE = "population_coverage_pct"
PRED_FIELD_GEO_COVERAGE = "geographic_coverage_pct"
PRED_FIELD_POP_TOTAL = "total_population_million"

_METRIC_KEYS = {"pop_weighted", "geo_mean"}
_RAW_METRIC_FIELDS = {
    "pop_weighted": FIELD_POP_WEIGHTED,
    "geo_mean": FIELD_GEO_MEAN,
}
_PRED_METRIC_FIELDS = {
    "pop_weighted": PRED_FIELD_POP_WEIGHTED,
    "geo_mean": PRED_FIELD_GEO_MEAN,
}

SourceKind = Literal["raw", "pred"]


def _safe_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


PRED_START_YEAR = _safe_int(os.getenv("ACAG_PRED_START_YEAR"), 2020)


def _metric_key(metric: str) -> str:
    key = (metric or "").strip().lower()
    if key not in _METRIC_KEYS:
        raise ValueError("metric must be one of ['pop_weighted', 'geo_mean']")
    return key


def _to_country_key(value: str) -> str:
    canonical = normalize_country_name(value).strip().lower()
    return re.sub(r"[^a-z0-9]+", " ", canonical).strip()


def _build_country_or(names: list[str], field_name: str) -> list[dict[str, dict[str, str]]]:
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
                    field_name: {
                        "$regex": f"^{re.escape(candidate)}$",
                        "$options": "i",
                    }
                }
            )
    if not clauses:
        clauses.append({field_name: exact_country_regex(names[0])})
    return clauses


def _pred_country_clauses(names: list[str]) -> list[dict[str, Any]]:
    keys: set[str] = set()
    for name in names:
        for candidate in country_aliases(name):
            key = _to_country_key(candidate)
            if key:
                keys.add(key)

    clauses: list[dict[str, Any]] = []
    if keys:
        clauses.append({PRED_FIELD_COUNTRY_KEY: {"$in": sorted(keys)}})
    clauses.extend(_build_country_or(names, PRED_FIELD_REGION))
    clauses.extend(_build_country_or(names, PRED_FIELD_SOURCE_REGION))
    return clauses


def _convert_expr(expr) -> dict:
    return {"$convert": {"input": expr, "to": "double", "onError": None, "onNull": None}}


def _convert_int_expr(expr) -> dict:
    return {"$convert": {"input": expr, "to": "int", "onError": None, "onNull": None}}


def _metric_value_expr_raw(metric_field: str) -> dict:
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


def _metric_value_expr(kind: SourceKind, metric_key: str) -> dict:
    if kind == "raw":
        return _metric_value_expr_raw(_RAW_METRIC_FIELDS[metric_key])
    return _convert_expr(f"${_PRED_METRIC_FIELDS[metric_key]}")


def _population_value_expr(kind: SourceKind) -> dict:
    if kind == "raw":
        return _convert_expr(f"${FIELD_POP_TOTAL}")
    return _convert_expr(f"${PRED_FIELD_POP_TOTAL}")


def _region_value_expr(kind: SourceKind):
    if kind == "raw":
        return f"${FIELD_REGION}"
    return {"$ifNull": [f"${PRED_FIELD_REGION}", f"${PRED_FIELD_SOURCE_REGION}"]}


def _year_value_expr(kind: SourceKind):
    if kind == "raw":
        return _convert_int_expr(f"${FIELD_YEAR}")
    return _convert_int_expr(f"${PRED_FIELD_YEAR}")


def _list_projection(kind: SourceKind) -> dict[str, Any]:
    if kind == "raw":
        return {
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

    return {
        "_id": 0,
        FIELD_REGION: _region_value_expr("pred"),
        FIELD_YEAR: _year_value_expr("pred"),
        FIELD_POP_WEIGHTED: _convert_expr(f"${PRED_FIELD_POP_WEIGHTED}"),
        FIELD_GEO_MEAN: _convert_expr(f"${PRED_FIELD_GEO_MEAN}"),
        FIELD_POP_COVERAGE: _convert_expr(f"${PRED_FIELD_POP_COVERAGE}"),
        FIELD_GEO_COVERAGE: _convert_expr(f"${PRED_FIELD_GEO_COVERAGE}"),
        FIELD_POP_TOTAL: _convert_expr(f"${PRED_FIELD_POP_TOTAL}"),
        "metric_value": 1,
    }


def _kind_for_year(year: int) -> SourceKind:
    return "pred" if int(year) >= PRED_START_YEAR else "raw"


def _get_collection(kind: SourceKind):
    return get_acag_collection() if kind == "raw" else get_acag_pred_collection()


def _build_filters(params: dict[str, Any], kind: SourceKind) -> dict[str, Any]:
    filters: dict[str, Any] = {}

    year = params.get("year")
    if year is not None:
        year_field = FIELD_YEAR if kind == "raw" else PRED_FIELD_YEAR
        filters[year_field] = int(year)

    country_names = params.get("country_names")
    if country_names:
        names = [name for name in country_names if isinstance(name, str) and name.strip()]
        if names:
            if kind == "raw":
                filters["$or"] = _build_country_or(names, FIELD_REGION)
            else:
                filters["$or"] = _pred_country_clauses(names)
    else:
        country_name = params.get("country_name")
        if country_name:
            if kind == "raw":
                filters["$or"] = _build_country_or([country_name], FIELD_REGION)
            else:
                filters["$or"] = _pred_country_clauses([country_name])

    return filters


def _list_from_collection(
    kind: SourceKind,
    params: dict[str, Any],
    limit: int,
    offset: int,
    metric_key: str,
):
    col = _get_collection(kind)
    filters = _build_filters(params, kind)
    metric_expr = _metric_value_expr(kind, metric_key)

    pipeline = [
        {"$match": filters},
        {"$addFields": {"metric_value": metric_expr}},
        {"$match": {"metric_value": {"$type": "number"}}},
        {"$sort": {"metric_value": -1}},
        {"$skip": int(offset)},
        {"$limit": int(limit)},
        {"$project": _list_projection(kind)},
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


def list_acag(params: dict[str, Any], limit: int, offset: int, metric: str):
    metric_key = _metric_key(metric)
    year = params.get("year")
    if year is not None:
        kind = _kind_for_year(int(year))
    else:
        kind = "raw"
    return _list_from_collection(kind, params, limit=limit, offset=offset, metric_key=metric_key)


def _country_summary_from_collection(kind: SourceKind, params: dict[str, Any], metric_key: str):
    col = _get_collection(kind)
    filters = _build_filters(params, kind)
    metric_expr = _metric_value_expr(kind, metric_key)
    pop_expr = _population_value_expr(kind)
    region_expr = _region_value_expr(kind)

    pipeline = [
        {"$match": filters},
        {
            "$addFields": {
                "metric_value": metric_expr,
                "population_value": {"$ifNull": [pop_expr, 0]},
                "region_value": region_expr,
            }
        },
        {"$match": {"metric_value": {"$type": "number"}, "region_value": {"$type": "string"}}},
        {
            "$group": {
                "_id": "$region_value",
                "numerator": {"$sum": {"$multiply": ["$metric_value", "$population_value"]}},
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


def country_summary(params: dict[str, Any], metric: str):
    metric_key = _metric_key(metric)
    year = params.get("year")
    if year is not None:
        kind = _kind_for_year(int(year))
    else:
        kind = "raw"
    return _country_summary_from_collection(kind, params, metric_key=metric_key)


def _trend_segment(
    kind: SourceKind,
    year_from: int,
    year_to: int,
    metric_key: str,
    country_name: str | None,
):
    col = _get_collection(kind)
    params = {"country_name": country_name} if country_name else {}
    match = _build_filters(params, kind)
    year_field = FIELD_YEAR if kind == "raw" else PRED_FIELD_YEAR
    match[year_field] = {"$gte": int(year_from), "$lte": int(year_to)}

    metric_expr = _metric_value_expr(kind, metric_key)
    pop_expr = _population_value_expr(kind)
    year_expr = _year_value_expr(kind)

    pipeline = [
        {"$match": match},
        {
            "$addFields": {
                "metric_value": metric_expr,
                "population_value": {"$ifNull": [pop_expr, 0]},
                "year_value": year_expr,
            }
        },
        {"$match": {"metric_value": {"$type": "number"}, "year_value": {"$type": "number"}}},
        {
            "$group": {
                "_id": "$year_value",
                "numerator": {"$sum": {"$multiply": ["$metric_value", "$population_value"]}},
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


def trend_by_year(
    year_from: int,
    year_to: int,
    metric: str,
    country_name: str | None = None,
):
    metric_key = _metric_key(metric)
    start = int(min(year_from, year_to))
    end = int(max(year_from, year_to))

    by_year: dict[int, dict[str, Any]] = {}

    raw_end = min(end, PRED_START_YEAR - 1)
    if start <= raw_end:
        raw_rows = _trend_segment(
            "raw",
            year_from=start,
            year_to=raw_end,
            metric_key=metric_key,
            country_name=country_name,
        )
        for row in raw_rows:
            by_year[int(row["year"])] = row

    pred_start = max(start, PRED_START_YEAR)
    if pred_start <= end:
        pred_rows = _trend_segment(
            "pred",
            year_from=pred_start,
            year_to=end,
            metric_key=metric_key,
            country_name=country_name,
        )
        for row in pred_rows:
            by_year[int(row["year"])] = row

    return [by_year[y] for y in sorted(by_year)]
