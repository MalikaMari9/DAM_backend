from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.enums import OrgType, DataDomain, ApplicationStatus


class OrgApplicationBase(BaseModel):
    org_name: str
    org_type: OrgType
    data_domain: DataDomain
    country: str
    address_detail: str
    official_email: EmailStr
    website: Optional[str] = None
    contact_name: str
    contact_email: EmailStr


class OrgApplicationCreate(OrgApplicationBase):
    pass


class OrgApplicationUpdate(BaseModel):
    status: ApplicationStatus
    admin_note: Optional[str] = None


class OrgApplicationRead(OrgApplicationBase):
    application_id: int
    status: ApplicationStatus
    admin_note: Optional[str] = None
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True