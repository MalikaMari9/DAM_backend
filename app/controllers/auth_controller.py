from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.schemas.account_schema import AccountLogin, TokenResponse
from app.repositories.account_repo import get_account_by_email
from app.core.security import verify_password, create_access_token, hash_password
from app.repositories.account_repo import get_account_by_id, get_account_by_email
from app.repositories.password_reset_repo import (
    create_password_reset,
    get_valid_reset_by_token_hash,
    mark_reset_used,
)
from app.core.email import send_email
from app.core.config import get_settings
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import string


def login(db: Session, data: AccountLogin) -> TokenResponse:
    account = get_account_by_email(db, data.email)
    if not account or not verify_password(data.password, account.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(subject=str(account.account_id))
    return TokenResponse(access_token=token)


def change_password(db: Session, account_id: int, current_password: str, new_password: str):
    account = get_account_by_id(db, account_id)
    if not account or not verify_password(current_password, account.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    account.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(account)
    return {"status": "ok"}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _send_reset_email(to_email: str, reset_link: str):
    subject = "AirHealth: Reset Your Password"
    html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6;">
      <h2>Password reset</h2>
      <p>We received a request to reset your password.</p>
      <p>Click the link below to set a new password (valid for 30 minutes):</p>
      <p><a href="{reset_link}">{reset_link}</a></p>
      <p>If you did not request this, you can ignore this email.</p>
      <p>Thank you,<br/>AirHealth Team</p>
    </div>
    """
    send_email(to_email, subject, html)


def forgot_password(db: Session, email: str):
    account = get_account_by_email(db, email)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    create_password_reset(db, account.account_id, token_hash, expires_at)

    settings = get_settings()
    reset_link = f"{settings.frontend_base_url}/reset-password?token={token}"
    _send_reset_email(account.email, reset_link)
    return {"status": "ok"}


def reset_password(db: Session, token: str, new_password: str):
    token_hash = _hash_token(token)
    reset = get_valid_reset_by_token_hash(db, token_hash)
    if not reset:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    account = get_account_by_id(db, reset.account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    account.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(account)
    mark_reset_used(db, reset)
    return {"status": "ok"}
