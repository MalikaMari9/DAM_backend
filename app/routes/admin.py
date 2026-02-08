from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import require_admin
from app.schemas.admin_schema import AdminCreate, OrgAccountCreate
from app.controllers.admin_controller import create_admin_account, create_org_account

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/users/admin")
def create_admin_route(
    payload: AdminCreate,
    db: Session = Depends(get_db),
    _account=Depends(require_admin),
):
    return create_admin_account(db, payload)


@router.post("/users/org")
def create_org_route(
    payload: OrgAccountCreate,
    db: Session = Depends(get_db),
    _account=Depends(require_admin),
):
    return create_org_account(db, payload)
