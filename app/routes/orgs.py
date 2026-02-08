from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import require_admin, require_org
from app.controllers.org_controller import list_orgs, get_org, update_org_profile
from app.schemas.org_schema import OrgRead, OrgUpdate

router = APIRouter(prefix="/orgs", tags=["orgs"])


@router.get("", response_model=list[OrgRead])
def list_orgs_route(
    db: Session = Depends(get_db),
    _account=Depends(require_admin),
):
    return list_orgs(db)


@router.get("/me", response_model=OrgRead)
def get_my_org_route(
    db: Session = Depends(get_db),
    account=Depends(require_org),
):
    if not account.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return get_org(db, account.org_id)


@router.get("/{org_id}", response_model=OrgRead)
def get_org_route(
    org_id: int,
    db: Session = Depends(get_db),
    _account=Depends(require_admin),
):
    return get_org(db, org_id)


@router.patch("/{org_id}", response_model=OrgRead)
def update_org_route(
    org_id: int,
    payload: OrgUpdate,
    db: Session = Depends(get_db),
    _account=Depends(require_admin),
):
    return update_org_profile(db, org_id, payload)
