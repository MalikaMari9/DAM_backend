from pydantic import BaseModel, EmailStr
from app.models.enums import OrgType, DataDomain


class AdminCreate(BaseModel):
    name: str
    email: EmailStr


class OrgAccountCreate(BaseModel):
    org_name: str
    org_type: OrgType
    data_domain: DataDomain
    country: str
    official_email: EmailStr
    address_detail: str
    contact_name: str
    contact_email: EmailStr
