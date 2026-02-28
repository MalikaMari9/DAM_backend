from typing import Any
import os

from app.core.mongo import get_imhe_collection, get_imhe_pred_collection


def _safe_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


IMHE_PRED_START_YEAR = _safe_int(os.getenv("IMHE_PRED_START_YEAR"), 2024)


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


def _is_count_like_metric(params: dict[str, Any]) -> bool:
    metric_name = str(params.get("metric_name") or "").strip().lower()
    if metric_name:
        return metric_name in {"number", "count"}

    metric_id = params.get("metric_id")
    if metric_id is not None:
        try:
            return int(metric_id) == 1
        except (TypeError, ValueError):
            pass

    measure_name = str(params.get("measure_name") or "").strip().lower()
    if measure_name in {"deaths", "dalys (disability-adjusted life years)"}:
        return True

    return False


def _normalize_year_filter(year_filter: Any) -> dict[str, int] | None:
    if year_filter is None:
        return None
    if isinstance(year_filter, (int, float)):
        year = int(year_filter)
        return {"$gte": year, "$lte": year}
    if isinstance(year_filter, dict):
        normalized: dict[str, int] = {}
        if year_filter.get("$gte") is not None:
            normalized["$gte"] = int(year_filter["$gte"])
        if year_filter.get("$lte") is not None:
            normalized["$lte"] = int(year_filter["$lte"])
        return normalized or None
    return None


def _split_year_filter(year_filter: Any) -> tuple[dict[str, int] | None, dict[str, int] | None]:
    normalized = _normalize_year_filter(year_filter)
    raw_filter: dict[str, int] | None = None
    raw_upper = IMHE_PRED_START_YEAR - 1

    pred_filter: dict[str, int] | None = None
    pred_lower = IMHE_PRED_START_YEAR

    if normalized is None:
        raw_filter = {"$lte": raw_upper}
        pred_filter = {"$gte": pred_lower}
        return raw_filter, pred_filter

    gte = normalized.get("$gte")
    lte = normalized.get("$lte")

    effective_raw_upper = raw_upper if lte is None else min(lte, raw_upper)
    if gte is None or gte <= effective_raw_upper:
        raw_filter = {"$lte": effective_raw_upper}
        if gte is not None:
            raw_filter["$gte"] = gte

    effective_pred_lower = pred_lower if gte is None else max(gte, pred_lower)
    if lte is None or effective_pred_lower <= lte:
        pred_filter = {"$gte": effective_pred_lower}
        if lte is not None:
            pred_filter["$lte"] = lte

    return raw_filter, pred_filter


def _collection_for_point_year(params: dict[str, Any]):
    year = params.get("year")
    if isinstance(year, (int, float)):
        return get_imhe_pred_collection() if int(year) >= IMHE_PRED_START_YEAR else get_imhe_collection()
    return get_imhe_collection()


def _split_filters_by_source(params: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    base_params = dict(params)
    base_params.pop("year", None)
    base_filters = _build_filters(base_params)
    raw_year_filter, pred_year_filter = _split_year_filter(params.get("year"))

    raw_filters: dict[str, Any] | None = None
    pred_filters: dict[str, Any] | None = None

    if raw_year_filter is not None:
        raw_filters = dict(base_filters)
        raw_filters["year"] = raw_year_filter

    if pred_year_filter is not None:
        pred_filters = dict(base_filters)
        pred_filters["year"] = pred_year_filter

    return raw_filters, pred_filters


def _start_pipeline_for_sources(
    raw_filters: dict[str, Any] | None,
    pred_filters: dict[str, Any] | None,
    *,
    project: dict[str, Any] | None = None,
):
    raw_col = get_imhe_collection()
    pred_col = get_imhe_pred_collection()

    if raw_filters is None and pred_filters is None:
        return None, None

    if raw_filters is not None:
        pipeline: list[dict[str, Any]] = [{"$match": raw_filters}]
        if project is not None:
            pipeline.append({"$project": project})
        if pred_filters is not None:
            pred_pipeline: list[dict[str, Any]] = [{"$match": pred_filters}]
            if project is not None:
                pred_pipeline.append({"$project": project})
            pipeline.append(
                {
                    "$unionWith": {
                        "coll": pred_col.name,
                        "pipeline": pred_pipeline,
                    }
                }
            )
        return raw_col, pipeline

    if pred_filters is None:
        return None, None

    pipeline = [{"$match": pred_filters}]
    if project is not None:
        pipeline.append({"$project": project})
    return pred_col, pipeline


def _summary_for_collection(col):
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
        return total, agg[0].get("min_year"), agg[0].get("max_year")
    return total, None, None


def list_imhe(params: dict[str, Any], limit: int, offset: int):
    col = _collection_for_point_year(params)
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
    col = _collection_for_point_year(params)
    match = _build_filters(params)
    return sorted(col.distinct("location_name", match))


def summary():
    raw_total, raw_min, raw_max = _summary_for_collection(get_imhe_collection())
    pred_total, pred_min, pred_max = _summary_for_collection(get_imhe_pred_collection())

    years = [y for y in [raw_min, pred_min] if y is not None]
    max_years = [y for y in [raw_max, pred_max] if y is not None]
    return {
        "total_docs": int(raw_total) + int(pred_total),
        "min_year": min(years) if years else None,
        "max_year": max(max_years) if max_years else None,
    }


def country_summary(params: dict[str, Any]):
    col = _collection_for_point_year(params)
    filters = _build_filters(params)
    aggregate_op = "$sum" if _is_count_like_metric(params) else "$avg"

    pipeline = [
        {"$match": filters},
        {
            "$group": {
                "_id": "$location_name",
                "value": {aggregate_op: "$val"},
                "count": {"$sum": 1},
            }
        },
        {"$project": {"_id": 0, "country": "$_id", "value": 1, "count": 1}},
        {"$sort": {"country": 1}},
    ]
    return list(col.aggregate(pipeline))


def list_ages(params: dict[str, Any]):
    col = _collection_for_point_year(params)
    filters = _build_filters(params)
    pipeline = [
        {"$match": filters},
        {"$group": {"_id": {"age_id": "$age_id", "age_name": "$age_name"}}},
        {"$project": {"_id": 0, "age_id": "$_id.age_id", "age_name": "$_id.age_name"}},
        {"$sort": {"age_id": 1}},
    ]
    return list(col.aggregate(pipeline))


def list_sexes(params: dict[str, Any]):
    col = _collection_for_point_year(params)
    filters = _build_filters(params)
    pipeline = [
        {"$match": filters},
        {"$group": {"_id": {"sex_id": "$sex_id", "sex_name": "$sex_name"}}},
        {"$project": {"_id": 0, "sex_id": "$_id.sex_id", "sex_name": "$_id.sex_name"}},
        {"$sort": {"sex_id": 1}},
    ]
    return list(col.aggregate(pipeline))


def list_causes(params: dict[str, Any]):
    col = _collection_for_point_year(params)
    filters = _build_filters(params)
    pipeline = [
        {"$match": filters},
        {"$group": {"_id": {"cause_id": "$cause_id", "cause_name": "$cause_name"}}},
        {"$project": {"_id": 0, "cause_id": "$_id.cause_id", "cause_name": "$_id.cause_name"}},
        {"$sort": {"cause_name": 1}},
    ]
    return list(col.aggregate(pipeline))


def list_measures(params: dict[str, Any]):
    col = _collection_for_point_year(params)
    filters = _build_filters(params)
    pipeline = [
        {"$match": filters},
        {"$group": {"_id": {"measure_id": "$measure_id", "measure_name": "$measure_name"}}},
        {"$project": {"_id": 0, "measure_id": "$_id.measure_id", "measure_name": "$_id.measure_name"}},
        {"$sort": {"measure_name": 1}},
    ]
    return list(col.aggregate(pipeline))


def list_metrics(params: dict[str, Any]):
    col = _collection_for_point_year(params)
    filters = _build_filters(params)
    pipeline = [
        {"$match": filters},
        {"$group": {"_id": {"metric_id": "$metric_id", "metric_name": "$metric_name"}}},
        {"$project": {"_id": 0, "metric_id": "$_id.metric_id", "metric_name": "$_id.metric_name"}},
        {"$sort": {"metric_name": 1}},
    ]
    return list(col.aggregate(pipeline))


def _trend_by_year_from_collection(col, params: dict[str, Any]):
    filters = _build_filters(params)
    aggregate_op = "$sum" if _is_count_like_metric(params) else "$avg"
    pipeline = [
        {"$match": filters},
        {"$group": {"_id": "$year", "value": {aggregate_op: "$val"}}},
        {"$project": {"_id": 0, "year": "$_id", "value": 1}},
        {"$sort": {"year": 1}},
    ]
    return list(col.aggregate(pipeline))


def trend_by_year(params: dict[str, Any]):
    raw_year_filter, pred_year_filter = _split_year_filter(params.get("year"))

    merged: dict[int, dict[str, Any]] = {}

    if raw_year_filter is not None:
        raw_params = dict(params)
        raw_params["year"] = raw_year_filter
        for row in _trend_by_year_from_collection(get_imhe_collection(), raw_params):
            merged[int(row["year"])] = row

    if pred_year_filter is not None:
        pred_params = dict(params)
        pred_params["year"] = pred_year_filter
        for row in _trend_by_year_from_collection(get_imhe_pred_collection(), pred_params):
            merged[int(row["year"])] = row

    return [merged[year] for year in sorted(merged)]


def value_percentiles(params: dict[str, Any], pcts: list[float]):
    raw_filters, pred_filters = _split_filters_by_source(params)
    col, pipeline = _start_pipeline_for_sources(raw_filters, pred_filters)
    if col is None or pipeline is None:
        return {"percentiles": [], "min_val": None, "max_val": None, "count": 0}

    pipeline.extend([
        {
            "$group": {
                "_id": None,
                "percentiles": {"$percentile": {"input": "$val", "p": pcts, "method": "approximate"}},
                "min_val": {"$min": "$val"},
                "max_val": {"$max": "$val"},
                "count": {"$sum": 1},
            }
        },
        {"$project": {"_id": 0, "percentiles": 1, "min_val": 1, "max_val": 1, "count": 1}},
    ])
    res = list(col.aggregate(pipeline))
    return res[0] if res else {"percentiles": [], "min_val": None, "max_val": None, "count": 0}


def value_percentiles_dense_years(
    params: dict[str, Any], pcts: list[float], min_countries: int
):
    dense_params = dict(params)
    dense_params.pop("year", None)
    raw_filters, pred_filters = _split_filters_by_source(dense_params)
    col, year_pipeline = _start_pipeline_for_sources(
        raw_filters,
        pred_filters,
        project={"year": "$year", "location_name": "$location_name", "val": "$val"},
    )
    if col is None or year_pipeline is None:
        return {"percentiles": [], "min_val": None, "max_val": None, "count": 0}

    year_pipeline.extend([
        {"$group": {"_id": {"year": "$year", "country": "$location_name"}}},
        {"$group": {"_id": "$_id.year", "country_count": {"$sum": 1}}},
        {"$match": {"country_count": {"$gte": int(min_countries)}}},
        {"$sort": {"_id": 1}},
    ])
    dense_years = [row["_id"] for row in col.aggregate(year_pipeline)]
    if not dense_years:
        return {"percentiles": [], "min_val": None, "max_val": None, "count": 0}

    col, pipeline = _start_pipeline_for_sources(
        raw_filters,
        pred_filters,
        project={"year": "$year", "val": "$val"},
    )
    if col is None or pipeline is None:
        return {"percentiles": [], "min_val": None, "max_val": None, "count": 0}

    pipeline.extend([
        {"$match": {"year": {"$in": dense_years}}},
        {
            "$group": {
                "_id": None,
                "percentiles": {"$percentile": {"input": "$val", "p": pcts, "method": "approximate"}},
                "min_val": {"$min": "$val"},
                "max_val": {"$max": "$val"},
                "count": {"$sum": 1},
            }
        },
        {"$project": {"_id": 0, "percentiles": 1, "min_val": 1, "max_val": 1, "count": 1}},
    ])
    res = list(col.aggregate(pipeline))
    return res[0] if res else {"percentiles": [], "min_val": None, "max_val": None, "count": 0}
