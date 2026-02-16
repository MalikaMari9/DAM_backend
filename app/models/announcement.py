from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, Boolean, Enum as SAEnum, ForeignKey, CheckConstraint
from sqlalchemy.sql import func
from app.models.base import Base
from app.models.enums import AnnouncementType


class Announcement(Base):
    __tablename__ = "announcement_tbl"

    announcement_id = Column(BigInteger, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    type = Column(SAEnum(AnnouncementType, name="announcement_type_enum"), nullable=False, server_default="INFO")
    is_active = Column(Boolean, nullable=False, server_default="true")
    publish_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_by_account_id = Column(BigInteger, ForeignKey("account_tbl.account_id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("length(trim(both from title)) > 0", name="chk_announcement_title_not_blank"),
        CheckConstraint("length(trim(both from content)) > 0", name="chk_announcement_content_not_blank"),
        CheckConstraint("expires_at IS NULL OR expires_at > publish_at", name="chk_announcement_expiry_after_publish"),
    )