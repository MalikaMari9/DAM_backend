from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from app.models.base import Base


class OrgApplicationFile(Base):
    __tablename__ = "org_application_file_tbl"

    file_id = Column(BigInteger, primary_key=True, index=True)
    application_id = Column(BigInteger, ForeignKey("org_application_tbl.application_id", ondelete="CASCADE"), nullable=False)
    file_name = Column(Text, nullable=False)
    mime_type = Column(Text)
    storage_key = Column(Text, nullable=False)
    file_size_bytes = Column(BigInteger)
    uploaded_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())