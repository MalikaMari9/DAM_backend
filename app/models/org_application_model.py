from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, Enum as SAEnum
from sqlalchemy.sql import func
from app.models.base import Base
from app.models.enums import OrgType, DataDomain, ApplicationStatus


class OrgApplication(Base):
    __tablename__ = "org_application_tbl"

    application_id = Column(BigInteger, primary_key=True, index=True)
    org_name = Column(Text, nullable=False)
    org_type = Column(SAEnum(OrgType, name="org_type_enum"), nullable=False)
    data_domain = Column(SAEnum(DataDomain, name="data_domain_enum"), nullable=False)
    country = Column(Text, nullable=False)
    address_detail = Column(Text, nullable=False)
    official_email = Column(Text, nullable=False)
    website = Column(Text)
    contact_name = Column(Text, nullable=False)
    contact_email = Column(Text, nullable=False)
    status = Column(SAEnum(ApplicationStatus, name="application_status_enum"), nullable=False, server_default="PENDING")
    admin_note = Column(Text)
    submitted_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    reviewed_at = Column(TIMESTAMP(timezone=True))