from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from jose import JWTError
from app.core.db import get_db
from app.core.security import decode_access_token
from app.repositories.account_repo import get_account_by_id
from app.models.enums import AccountRole

security = HTTPBearer()


def get_current_account(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        if subject is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        account_id = int(subject)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    account = get_account_by_id(db, account_id)
    if not account or not account.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive account")
    return account


def require_admin(account=Depends(get_current_account)):
    if account.role != AccountRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return account


def require_org(account=Depends(get_current_account)):
    if account.role != AccountRole.ORG:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access required")
    return account
