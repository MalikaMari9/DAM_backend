from typing import Optional
import os

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/air", tags=["live-air"])

IQAIR_STATUS_HTTP = {
    "call_limit_reached": 429,
    "too_many_requests": 429,
    "incorrect_api_key": 503,
    "api_key_expired": 503,
    "feature_not_available": 503,
    "ip_location_failed": 502,
    "no_nearest_station": 404,
}

POLLUTANT_LABELS = {
    "p2": "PM2.5",
    "p1": "PM10",
    "o3": "O3",
    "n2": "NO2",
    "s2": "SO2",
    "co": "CO",
}


class LiveAirResponse(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    aqi_us: Optional[int] = None
    aqi_cn: Optional[int] = None
    category: Optional[str] = None
    main_pollutant: Optional[str] = None
    main_concentration: Optional[float] = None
    pm25: Optional[float] = None
    updated_at: Optional[str] = None
    temperature_c: Optional[float] = None
    humidity: Optional[int] = None


def _aqi_category(aqi: Optional[int]) -> Optional[str]:
    if aqi is None:
        return None
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    if aqi <= 200:
        return "Unhealthy"
    if aqi <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def _to_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@router.get("/live/nearest", response_model=LiveAirResponse)
async def get_live_air_nearest(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
):
    api_key = os.getenv("IQAIR_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="IQAir API key is not configured. Set IQAIR_API_KEY in backend/.env.",
        )

    base_url = os.getenv("IQAIR_BASE_URL", "https://api.airvisual.com/v2")
    url = f"{base_url.rstrip('/')}/nearest_city"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                url,
                params={"lat": lat, "lon": lon, "key": api_key},
            )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"IQAir request failed with status {exc.response.status_code}.",
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"IQAir request failed: {exc}")

    status = payload.get("status")
    if status != "success":
        raise HTTPException(
            status_code=IQAIR_STATUS_HTTP.get(str(status), 502),
            detail=f"IQAir error: {status or 'unknown_error'}",
        )

    data = payload.get("data") or {}
    current = data.get("current") or {}
    pollution = current.get("pollution") or {}
    weather = current.get("weather") or {}

    main_code = pollution.get("mainus")
    main_data = pollution.get(main_code) if isinstance(pollution.get(main_code), dict) else {}
    pm25_data = pollution.get("p2") if isinstance(pollution.get("p2"), dict) else {}

    aqi_us = _to_int(pollution.get("aqius"))

    return LiveAirResponse(
        city=data.get("city"),
        state=data.get("state"),
        country=data.get("country"),
        aqi_us=aqi_us,
        aqi_cn=_to_int(pollution.get("aqicn")),
        category=_aqi_category(aqi_us),
        main_pollutant=POLLUTANT_LABELS.get(main_code, main_code),
        main_concentration=_to_float(main_data.get("conc")),
        pm25=_to_float(pm25_data.get("conc")),
        updated_at=pollution.get("ts"),
        temperature_c=_to_float(weather.get("tp")),
        humidity=_to_int(weather.get("hu")),
    )
