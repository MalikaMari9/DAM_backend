from fastapi import APIRouter, Query, HTTPException, status
from app.controllers.pollution_acag_controller import (
    list_acag_items,
    get_acag_country_summary,
    get_acag_trend,
)
from app.schemas.pollution_acag_schema import (
    ACAGListResponse,
    ACAGTrendItem,
    ACAGCountrySummaryItem,
)


router = APIRouter(prefix="/pollution/acag", tags=["pollution-acag"])

ALLOWED_METRICS = {"pop_weighted", "geo_mean"}


@router.get("", response_model=ACAGListResponse)
def list_acag(
    year: int = Query(...),
    country_name: str | None = Query(default=None),
    country_names: list[str] | None = Query(default=None),
    metric: str = Query(default="pop_weighted"),
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
):
    metric_value = metric.strip().lower()
    if metric_value not in ALLOWED_METRICS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"metric must be one of {sorted(ALLOWED_METRICS)}",
        )
    filters = {
        "year": year,
        "country_name": country_name,
        "country_names": country_names,
    }
    total, items = list_acag_items(filters, limit=limit, offset=offset, metric=metric_value)
    return {"total": total, "items": items}


@router.get("/country-summary", response_model=list[ACAGCountrySummaryItem])
def acag_country_summary(
    year: int = Query(...),
    metric: str = Query(default="pop_weighted"),
    country_name: str | None = Query(default=None),
    country_names: list[str] | None = Query(default=None),
):
    metric_value = metric.strip().lower()
    if metric_value not in ALLOWED_METRICS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"metric must be one of {sorted(ALLOWED_METRICS)}",
        )
    filters = {
        "year": year,
        "country_name": country_name,
        "country_names": country_names,
    }
    return get_acag_country_summary(filters, metric=metric_value)


@router.get("/trend", response_model=list[ACAGTrendItem])
def acag_trend(
    year_from: int = Query(...),
    year_to: int = Query(...),
    metric: str = Query(default="pop_weighted"),
    country_name: str | None = Query(default=None),
):
    metric_value = metric.strip().lower()
    if metric_value not in ALLOWED_METRICS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"metric must be one of {sorted(ALLOWED_METRICS)}",
        )
    return get_acag_trend(
        year_from=year_from,
        year_to=year_to,
        metric=metric_value,
        country_name=country_name,
    )
