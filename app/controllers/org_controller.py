from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.schemas.org_schema import OrgCreate, OrgUpdate
from app.repositories.org_repo import get_org_by_id, get_orgs, create_org, update_org


def list_orgs(db: Session):
    return get_orgs(db)


def get_org(db: Session, org_id: int):
    org = get_org_by_id(db, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


def create_org_account(db: Session, data: OrgCreate):
    return create_org(db, data)


def update_org_profile(db: Session, org_id: int, data: OrgUpdate):
    org = get_org_by_id(db, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return update_org(db, org, data)