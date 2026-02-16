from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.models.enums import AnnouncementType


class AnnouncementBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    type: AnnouncementType = AnnouncementType.INFO
    is_active: bool = True
    publish_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class AnnouncementCreate(AnnouncementBase):
    pass


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1)
    type: Optional[AnnouncementType] = None
    is_active: Optional[bool] = None
    publish_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class AnnouncementInDB(AnnouncementBase):
    announcement_id: int
    created_by_account_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnnouncementResponse(AnnouncementInDB):
    pass


class AnnouncementListResponse(BaseModel):
    items: list[AnnouncementResponse]
    total: int