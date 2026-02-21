from fastapi import APIRouter, Query, HTTPException, status
from app.controllers.pollution_who_controller import (
    list_who_items,
    get_who_country_summary,
    get_who_trend,
)
from app.schemas.pollution_who_schema import WHOListResponse, WHOTrendItem, WHOCountrySummaryItem


router = APIRouter(prefix="/pollution/who", tags=["pollution-who"])

ALLOWED_METRICS = {"pm25", "pm10", "no2"}


@router.get("", response_model=WHOListResponse)
def list_who(
    year: int = Query(...),
    country_name: str | None = Query(default=None),
    country_names: list[str] | None = Query(default=None),
    metric: str = Query(default="pm25"),
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
    total, items = list_who_items(filters, limit=limit, offset=offset, metric=metric_value)
    return {"total": total, "items": items}


@router.get("/country-summary", response_model=list[WHOCountrySummaryItem])
def who_country_summary(
    year: int = Query(...),
    metric: str = Query(default="pm25"),
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
    return get_who_country_summary(filters, metric=metric_value)


@router.get("/trend", response_model=list[WHOTrendItem])
def who_trend(
    year_from: int = Query(...),
    year_to: int = Query(...),
    metric: str = Query(default="pm25"),
    country_name: str | None = Query(default=None),
):
    metric_value = metric.strip().lower()
    if metric_value not in ALLOWED_METRICS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"metric must be one of {sorted(ALLOWED_METRICS)}",
        )
    return get_who_trend(
        year_from=year_from,
        year_to=year_to,
        metric=metric_value,
        country_name=country_name,
    )
