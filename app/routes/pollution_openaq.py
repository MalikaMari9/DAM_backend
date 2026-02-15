from fastapi import APIRouter, Query, HTTPException, status
import httpx
from app.controllers.pollution_openaq_controller import (
    list_openaq_items,
    get_openaq_trend,
    get_openaq_pollutants,
    get_openaq_units,
    get_openaq_locations,
)
from app.schemas.pollution_openaq_schema import OpenAQListResponse, OpenAQTrendItem

router = APIRouter(prefix="/pollution/openaq", tags=["pollution-openaq"])

ALLOWED_METRICS = {"value", "avg", "min", "max", "median"}


@router.get("", response_model=OpenAQListResponse)
def list_openaq(
    year: int = Query(...),
    country_name: str | None = Query(default=None),
    country_names: list[str] | None = Query(default=None),
    pollutant: str | None = Query(default=None),
    metric: str = Query(default="value"),
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
        "pollutant": pollutant,
    }
    total, items = list_openaq_items(filters, limit=limit, offset=offset, metric=metric_value)
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


@router.get("/pollutants")
def openaq_pollutants(country_name: str | None = Query(default=None)):
    return {"items": get_openaq_pollutants(country_name=country_name)}


@router.get("/units")
def openaq_units(
    country_name: str | None = Query(default=None),
    pollutant: str | None = Query(default=None),
):
    return {"items": get_openaq_units(country_name=country_name, pollutant=pollutant)}


@router.get("/locations")
def openaq_locations(
    country_name: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    return {"items": get_openaq_locations(country_name=country_name, query=q, limit=limit)}


@router.get("/geocode")
def openaq_geocode(q: str, limit: int = Query(default=5, ge=1, le=10)):
    try:
        res = httpx.get(
            "https://nominatim.openstreetmap.org/search",
            params={"format": "json", "q": q, "limit": limit},
            headers={"User-Agent": "AirHealth/1.0"},
            timeout=10.0,
        )
        res.raise_for_status()
        return {"items": res.json()}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Geocode failed: {exc}")


@router.get("/reverse")
def openaq_reverse(lat: float, lon: float, zoom: int = Query(default=6, ge=3, le=10)):
    try:
        res = httpx.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"format": "json", "lat": lat, "lon": lon, "zoom": zoom},
            headers={"User-Agent": "AirHealth/1.0"},
            timeout=10.0,
        )
        res.raise_for_status()
        return res.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Reverse geocode failed: {exc}")
