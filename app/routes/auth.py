from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import get_current_account
from app.controllers.auth_controller import login, change_password, forgot_password, reset_password
from app.schemas.account_schema import (
    AccountLogin,
    TokenResponse,
    AccountRead,
    PasswordChange,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login_route(payload: AccountLogin, db: Session = Depends(get_db)):
    return login(db, payload)


@router.get("/me", response_model=AccountRead)
def me_route(account=Depends(get_current_account)):
    return account


@router.post("/change-password")
def change_password_route(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    return change_password(db, account.account_id, payload.current_password, payload.new_password)


@router.post("/forgot-password")
def forgot_password_route(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    return forgot_password(db, payload.email)


@router.post("/reset-password")
def reset_password_route(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    return reset_password(db, payload.token, payload.new_password)
