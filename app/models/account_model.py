from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, Boolean, Enum as SAEnum, ForeignKey
from sqlalchemy.sql import func
from app.models.base import Base
from app.models.enums import AccountRole


class Account(Base):
    __tablename__ = "account_tbl"

    account_id = Column(BigInteger, primary_key=True, index=True)
    email = Column(Text, nullable=False, unique=True, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(SAEnum(AccountRole, name="account_role_enum"), nullable=False)
    org_id = Column(BigInteger, ForeignKey("org_tbl.org_id", ondelete="SET NULL"))
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
