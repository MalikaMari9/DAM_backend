from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class OrgApplicationFileBase(BaseModel):
    file_name: str
    mime_type: Optional[str] = None
    storage_key: str
    file_size_bytes: Optional[int] = None


class OrgApplicationFileCreate(OrgApplicationFileBase):
    application_id: int


class OrgApplicationFileRead(OrgApplicationFileBase):
    file_id: int
    application_id: int
    uploaded_at: datetime

    class Config:
        from_attributes = True