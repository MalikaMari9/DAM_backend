from pydantic import BaseModel
from typing import Optional


class IMHERecord(BaseModel):
    population_group_id: int
    population_group_name: str
    measure_id: int
    measure_name: str
    location_id: int
    location_name: str
    sex_id: int
    sex_name: str
    age_id: int
    age_name: str
    cause_id: int
    cause_name: str
    metric_id: int
    metric_name: str
    year: int
    val: float
    upper: float
    lower: float
    source_file: Optional[str] = None


class IMHEListResponse(BaseModel):
    total: int
    items: list[IMHERecord]


class IMHESummary(BaseModel):
    total_docs: int
    min_year: Optional[int] = None
    max_year: Optional[int] = None


class IMHECountrySummaryItem(BaseModel):
    country: str
    value: float
    count: int


class IMHEAgeItem(BaseModel):
    age_id: int
    age_name: str


class IMHESexItem(BaseModel):
    sex_id: int
    sex_name: str


class IMHECauseItem(BaseModel):
    cause_id: int
    cause_name: str
