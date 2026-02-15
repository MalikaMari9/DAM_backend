from fastapi import APIRouter, Query
from app.controllers.health_imhe_controller import (
    get_imhe_list,
    get_imhe_locations,
    get_imhe_summary,
    get_imhe_country_summary,
    get_imhe_ages,
    get_imhe_sexes,
    get_imhe_causes,
    get_imhe_measures,
    get_imhe_metrics,
    get_imhe_value_percentiles,
    get_imhe_value_percentiles_dense,
    get_imhe_trend,
    get_imhe_country_summary_with_pollution,
)
from app.schemas.health_imhe_schema import (
    IMHEListResponse,
    IMHESummary,
    IMHECountrySummaryItem,
    IMHECountryPollutionSummaryItem,
    IMHEAgeItem,
    IMHESexItem,
    IMHECauseItem,
    IMHEMeasureItem,
    IMHEMetricItem,
    IMHEValuePercentiles,
    IMHEYearValueItem,
)

router = APIRouter(prefix="/health/imhe", tags=["health-imhe"])
EXCLUDED_AGE_NAMES = {
    "10-14 years",
    "15-19 years",
    "All ages",
    "<1 year",
    "50-69 years",
    "80-84 years",
    "85-89 years",
    "90-94 years",
    "95+ years",
}


@router.get("", response_model=IMHEListResponse)
def list_imhe(
    year: int | None = Query(default=None),
    location_id: int | None = Query(default=None),
    cause_id: int | None = Query(default=None),
    age_id: int | None = Query(default=None),
    sex_id: int | None = Query(default=None),
    measure_id: int | None = Query(default=None),
    metric_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    filters = {
        "exclude_age_names": EXCLUDED_AGE_NAMES,
        "year": year,
        "location_id": location_id,
        "cause_id": cause_id,
        "age_id": age_id,
        "sex_id": sex_id,
        "measure_id": measure_id,
        "metric_id": metric_id,
    }
    total, items = get_imhe_list(filters, limit=limit, offset=offset)
    return {"total": total, "items": items}


@router.get("/summary", response_model=IMHESummary)
def imhe_summary():
    return get_imhe_summary()


@router.get("/locations", response_model=list[str])
def imhe_locations(
    year: int | None = Query(default=None),
    measure_name: str | None = Query(default=None),
    cause_name_contains: str | None = Query(default=None),
    sex_name: str | None = Query(default=None),
):
    filters = {
        "exclude_age_names": EXCLUDED_AGE_NAMES,
        "year": year,
        "measure_name": measure_name,
        "cause_name_contains": cause_name_contains,
        "sex_name": sex_name,
    }
    return get_imhe_locations(filters)


@router.get("/country-summary", response_model=list[IMHECountrySummaryItem])
def imhe_country_summary(
    year: int = Query(...),
    location_id: int | None = Query(default=None),
    cause_id: int | None = Query(default=None),
    age_id: int | None = Query(default=None),
    sex_id: int | None = Query(default=None),
    measure_id: int | None = Query(default=None),
    metric_id: int | None = Query(default=None),
    measure_name: str | None = Query(default=None),
    metric_name: str | None = Query(default=None),
    cause_name: str | None = Query(default=None),
    cause_name_contains: str | None = Query(default=None),
    age_name: str | None = Query(default=None),
    sex_name: str | None = Query(default=None),
    location_name: str | None = Query(default=None),
):
    filters = {
        "exclude_age_names": EXCLUDED_AGE_NAMES,
        "year": year,
        "location_id": location_id,
        "cause_id": cause_id,
        "age_id": age_id,
        "sex_id": sex_id,
        "measure_id": measure_id,
        "metric_id": metric_id,
        "measure_name": measure_name,
        "metric_name": metric_name,
        "cause_name": cause_name,
        "cause_name_contains": cause_name_contains,
        "age_name": age_name,
        "sex_name": sex_name,
        "location_name": location_name,
    }
    return get_imhe_country_summary(filters)


@router.get("/country-summary-with-pollution", response_model=list[IMHECountryPollutionSummaryItem])
def imhe_country_summary_with_pollution(
    year: int = Query(...),
    pollutant: str = Query(default="PM2.5"),
    location_id: int | None = Query(default=None),
    cause_id: int | None = Query(default=None),
    age_id: int | None = Query(default=None),
    sex_id: int | None = Query(default=None),
    measure_id: int | None = Query(default=None),
    metric_id: int | None = Query(default=None),
    measure_name: str | None = Query(default=None),
    metric_name: str | None = Query(default=None),
    cause_name: str | None = Query(default=None),
    cause_name_contains: str | None = Query(default=None),
    age_name: str | None = Query(default=None),
    sex_name: str | None = Query(default=None),
    location_name: str | None = Query(default=None),
):
    filters = {
        "exclude_age_names": EXCLUDED_AGE_NAMES,
        "year": year,
        "location_id": location_id,
        "cause_id": cause_id,
        "age_id": age_id,
        "sex_id": sex_id,
        "measure_id": measure_id,
        "metric_id": metric_id,
        "measure_name": measure_name,
        "metric_name": metric_name,
        "cause_name": cause_name,
        "cause_name_contains": cause_name_contains,
        "age_name": age_name,
        "sex_name": sex_name,
        "location_name": location_name,
    }
    return get_imhe_country_summary_with_pollution(filters, pollutant=pollutant)


@router.get("/ages", response_model=list[IMHEAgeItem])
def imhe_ages(
    year: int | None = Query(default=None),
    measure_name: str | None = Query(default=None),
    metric_name: str | None = Query(default=None),
    cause_name: str | None = Query(default=None),
    cause_name_contains: str | None = Query(default=None),
    sex_name: str | None = Query(default=None),
    location_name: str | None = Query(default=None),
):
    filters = {
        "exclude_age_names": EXCLUDED_AGE_NAMES,
        "year": year,
        "measure_name": measure_name,
        "metric_name": metric_name,
        "cause_name": cause_name,
        "cause_name_contains": cause_name_contains,
        "sex_name": sex_name,
        "location_name": location_name,
    }
    return get_imhe_ages(filters)


@router.get("/sexes", response_model=list[IMHESexItem])
def imhe_sexes(
    year: int | None = Query(default=None),
    measure_name: str | None = Query(default=None),
    metric_name: str | None = Query(default=None),
    cause_name: str | None = Query(default=None),
    cause_name_contains: str | None = Query(default=None),
    age_name: str | None = Query(default=None),
    location_name: str | None = Query(default=None),
):
    filters = {
        "exclude_age_names": EXCLUDED_AGE_NAMES,
        "year": year,
        "measure_name": measure_name,
        "metric_name": metric_name,
        "cause_name": cause_name,
        "cause_name_contains": cause_name_contains,
        "age_name": age_name,
        "location_name": location_name,
    }
    return get_imhe_sexes(filters)


@router.get("/causes", response_model=list[IMHECauseItem])
def imhe_causes(
    year: int | None = Query(default=None),
    measure_name: str | None = Query(default=None),
    metric_name: str | None = Query(default=None),
    age_name: str | None = Query(default=None),
    sex_name: str | None = Query(default=None),
    location_name: str | None = Query(default=None),
):
    filters = {
        "exclude_age_names": EXCLUDED_AGE_NAMES,
        "year": year,
        "measure_name": measure_name,
        "metric_name": metric_name,
        "age_name": age_name,
        "sex_name": sex_name,
        "location_name": location_name,
    }
    return get_imhe_causes(filters)


@router.get("/measures", response_model=list[IMHEMeasureItem])
def imhe_measures(
    year: int | None = Query(default=None),
    cause_name: str | None = Query(default=None),
    age_name: str | None = Query(default=None),
    sex_name: str | None = Query(default=None),
    location_name: str | None = Query(default=None),
):
    filters = {
        "exclude_age_names": EXCLUDED_AGE_NAMES,
        "year": year,
        "cause_name": cause_name,
        "age_name": age_name,
        "sex_name": sex_name,
        "location_name": location_name,
    }
    return get_imhe_measures(filters)


@router.get("/metrics", response_model=list[IMHEMetricItem])
def imhe_metrics(
    year: int | None = Query(default=None),
    cause_name: str | None = Query(default=None),
    age_name: str | None = Query(default=None),
    sex_name: str | None = Query(default=None),
    location_name: str | None = Query(default=None),
):
    filters = {
        "exclude_age_names": EXCLUDED_AGE_NAMES,
        "year": year,
        "cause_name": cause_name,
        "age_name": age_name,
        "sex_name": sex_name,
        "location_name": location_name,
    }
    return get_imhe_metrics(filters)


@router.get("/trend", response_model=list[IMHEYearValueItem])
def imhe_trend(
    measure_name: str | None = Query(default=None),
    metric_name: str | None = Query(default=None),
    cause_name: str | None = Query(default=None),
    age_name: str | None = Query(default=None),
    sex_name: str | None = Query(default=None),
    location_name: str | None = Query(default=None),
):
    filters = {
        "exclude_age_names": EXCLUDED_AGE_NAMES,
        "measure_name": measure_name,
        "metric_name": metric_name,
        "cause_name": cause_name,
        "age_name": age_name,
        "sex_name": sex_name,
        "location_name": location_name,
    }
    return get_imhe_trend(filters)


@router.get("/percentiles", response_model=IMHEValuePercentiles)
def imhe_percentiles(
    p: list[float] = Query(default=[0.05, 0.95]),
    dense_years: bool = Query(default=True),
    min_countries: int = Query(default=150, ge=1),
    year_from: int | None = Query(default=None),
    year_to: int | None = Query(default=None),
    measure_name: str | None = Query(default=None),
    metric_name: str | None = Query(default=None),
    cause_name: str | None = Query(default=None),
    age_name: str | None = Query(default=None),
    sex_name: str | None = Query(default=None),
    location_name: str | None = Query(default=None),
):
    filters = {
        "exclude_age_names": EXCLUDED_AGE_NAMES,
        "measure_name": measure_name,
        "metric_name": metric_name,
        "cause_name": cause_name,
        "age_name": age_name,
        "sex_name": sex_name,
        "location_name": location_name,
    }
    if year_from is not None or year_to is not None:
        year_filter: dict[str, int] = {}
        if year_from is not None:
            year_filter["$gte"] = year_from
        if year_to is not None:
            year_filter["$lte"] = year_to
        filters["year"] = year_filter
    if dense_years:
        return get_imhe_value_percentiles_dense(filters, p, min_countries)
    return get_imhe_value_percentiles(filters, p)
