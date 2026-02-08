from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from app.models.base import Base


class PasswordReset(Base):
    __tablename__ = "password_reset_tbl"

    reset_id = Column(BigInteger, primary_key=True, index=True)
    account_id = Column(BigInteger, ForeignKey("account_tbl.account_id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(Text, nullable=False, unique=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    used_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
