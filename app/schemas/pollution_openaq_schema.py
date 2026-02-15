from pydantic import BaseModel
from typing import Optional


class OpenAQItem(BaseModel):
    location_name: str
    pollutant: str
    units: str
    coverage_percent: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    country_name: Optional[str] = None
    country_code: Optional[str] = None
    year: Optional[int] = None
    value: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    median: Optional[float] = None
    avg: Optional[float] = None
    metric: str
    metric_value: Optional[float] = None


class OpenAQListResponse(BaseModel):
    total: int
    items: list[OpenAQItem]


class OpenAQTrendItem(BaseModel):
    year: int
    value: float | None = None
