from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from app.models.enums import AccountRole


class AccountBase(BaseModel):
    email: EmailStr
    role: AccountRole
    org_id: Optional[int] = None
    is_active: bool = True


class AccountCreate(AccountBase):
    password: str


class AccountRead(AccountBase):
    account_id: int

    model_config = ConfigDict(from_attributes=True)


class AccountLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
