from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, Enum as SAEnum, ForeignKey
from sqlalchemy.sql import func
from app.models.base import Base
from app.models.enums import DataDomain, UploadStatus


class Upload(Base):
    __tablename__ = "upload_tbl"

    upload_id = Column(BigInteger, primary_key=True, index=True)
    account_id = Column(BigInteger, ForeignKey("account_tbl.account_id", ondelete="RESTRICT"), nullable=False)
    org_id = Column(BigInteger, ForeignKey("org_tbl.org_id", ondelete="RESTRICT"), nullable=False)
    data_domain = Column(SAEnum(DataDomain, name="data_domain_enum"), nullable=False)
    mongo_collection = Column(Text, nullable=False)
    mongo_ref_id = Column(Text, nullable=False)
    country = Column(Text, nullable=False)
    status = Column(SAEnum(UploadStatus, name="upload_status_enum"), nullable=False, server_default="RECEIVED")
    error_message = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
