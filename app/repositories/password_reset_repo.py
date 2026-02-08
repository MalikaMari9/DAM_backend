from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.password_reset_model import PasswordReset


def create_password_reset(db: Session, account_id: int, token_hash: str, expires_at: datetime) -> PasswordReset:
    reset = PasswordReset(
        account_id=account_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(reset)
    db.commit()
    db.refresh(reset)
    return reset


def get_valid_reset_by_token_hash(db: Session, token_hash: str) -> PasswordReset | None:
    now = datetime.now(timezone.utc)
    stmt = (
        select(PasswordReset)
        .where(PasswordReset.token_hash == token_hash)
        .where(PasswordReset.used_at.is_(None))
        .where(PasswordReset.expires_at > now)
    )
    return db.execute(stmt).scalars().first()


def mark_reset_used(db: Session, reset: PasswordReset):
    reset.used_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(reset)
    return reset
