from pydantic import BaseModel
from typing import Optional


class ACAGItem(BaseModel):
    location_name: Optional[str] = None
    pollutant: str
    units: str
    coverage_percent: Optional[float] = None
    country_name: Optional[str] = None
    year: Optional[int] = None
    value: Optional[float] = None
    metric: str
    metric_value: Optional[float] = None
    population_million: Optional[float] = None
    geographic_coverage_percent: Optional[float] = None


class ACAGListResponse(BaseModel):
    total: int
    items: list[ACAGItem]


class ACAGTrendItem(BaseModel):
    year: int
    value: float | None = None


class ACAGCountrySummaryItem(BaseModel):
    country: str
    value: float | None = None
    count: int
