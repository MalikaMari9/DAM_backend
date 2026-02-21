from pydantic import BaseModel
from typing import Optional


class WHOItem(BaseModel):
    location_name: Optional[str] = None
    pollutant: str
    units: str
    coverage_percent: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    country_name: Optional[str] = None
    country_code: Optional[str] = None
    year: Optional[int] = None
    value: Optional[float] = None
    population: Optional[float] = None
    who_region: Optional[str] = None
    city: Optional[str] = None
    metric: str
    metric_value: Optional[float] = None


class WHOListResponse(BaseModel):
    total: int
    items: list[WHOItem]


class WHOTrendItem(BaseModel):
    year: int
    value: float | None = None


class WHOCountrySummaryItem(BaseModel):
    country: str
    value: float | None = None
    count: int
