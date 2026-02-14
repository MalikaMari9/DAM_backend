from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.enums import OrgStatus, OrgType, DataDomain


class OrgBase(BaseModel):
    org_name: str
    org_type: OrgType
    data_domain: DataDomain
    country: str
    address_detail: str
    official_email: EmailStr
    website: Optional[str] = None
    contact_name: str
    contact_email: EmailStr


class OrgCreate(OrgBase):
    pass


class OrgUpdate(BaseModel):
    org_name: Optional[str] = None
    org_type: Optional[OrgType] = None
    data_domain: Optional[DataDomain] = None
    country: Optional[str] = None
    address_detail: Optional[str] = None
    official_email: Optional[EmailStr] = None
    website: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    status: Optional[OrgStatus] = None


class OrgRead(OrgBase):
    org_id: int
    status: OrgStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
