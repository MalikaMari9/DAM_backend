from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.enums import DataDomain, UploadStatus


class UploadCreate(BaseModel):
    mongo_collection: str
    mongo_ref_id: str


class UploadRead(BaseModel):
    upload_id: int
    account_id: int
    org_id: int
    data_domain: DataDomain
    mongo_collection: str
    mongo_ref_id: str
    country: str
    status: UploadStatus
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UploadUpdateStatus(BaseModel):
    status: UploadStatus
    error_message: Optional[str] = None


class HealthIMHERecordManual(BaseModel):
    measure_name: str
    location_name: str
    sex_name: str
    age_name: str
    cause_name: str
    metric_name: str
    year: int
    val: float
    upper: float | None = None
    lower: float | None = None


class UploadRecordList(BaseModel):
    total: int
    items: list[dict]


class UploadRecordUpdate(BaseModel):
    measure_name: str
    sex_name: str
    age_name: str
    cause_name: str
    metric_name: str
    year: int
    val: float
    upper: float | None = None
    lower: float | None = None
