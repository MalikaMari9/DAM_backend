from fastapi import APIRouter, Query, HTTPException, status
from app.controllers.pollution_openaq_controller import list_openaq_items, get_openaq_trend
from app.schemas.pollution_openaq_schema import OpenAQListResponse, OpenAQTrendItem

router = APIRouter(prefix="/pollution/openaq", tags=["pollution-openaq"])

ALLOWED_METRICS = {"value", "avg", "min", "max", "median"}


@router.get("", response_model=OpenAQListResponse)
def list_openaq(
    year: int = Query(...),
    country_name: str | None = Query(default=None),
    pollutant: str | None = Query(default=None),
    metric: str = Query(default="value"),
    limit: int = Query(default=1000, ge=1, le=5000),
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
        "pollutant": pollutant,
    }
    total, items = list_openaq_items(filters, limit=limit, metric=metric_value)
    return {"total": total, "items": items}


@router.get("/trend", response_model=list[OpenAQTrendItem])
def openaq_trend(
    year_from: int = Query(...),
    year_to: int = Query(...),
    pollutant: str | None = Query(default=None),
    country_name: str | None = Query(default=None),
    metric: str = Query(default="avg"),
    method: str = Query(default="weighted"),
):
    metric_value = metric.strip().lower()
    if metric_value not in ALLOWED_METRICS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"metric must be one of {sorted(ALLOWED_METRICS)}",
        )
    method_value = method.strip().lower()
    if method_value not in {"weighted", "unweighted", "balanced", "median"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="method must be one of ['weighted', 'unweighted', 'balanced', 'median']",
        )
    return get_openaq_trend(
        year_from=year_from,
        year_to=year_to,
        pollutant=pollutant,
        country_name=country_name,
        metric=metric_value,
        method=method_value,
    )
