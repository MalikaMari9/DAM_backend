from pydantic import BaseModel
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

    class Config:
        from_attributes = True


class UploadUpdateStatus(BaseModel):
    status: UploadStatus
    error_message: Optional[str] = None
