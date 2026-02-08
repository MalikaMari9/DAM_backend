from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.account_model import Account
from app.models.enums import AccountRole
from app.repositories.org_repo import get_org_by_id
from app.repositories.upload_repo import (
    create_upload,
    list_uploads,
    list_uploads_by_org,
    get_upload_by_id,
    update_upload_status,
)
from app.schemas.upload_schema import UploadCreate, UploadUpdateStatus


def create_org_upload(db: Session, account: Account, data: UploadCreate):
    if account.role != AccountRole.ORG or not account.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access required")
    org = get_org_by_id(db, account.org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    return create_upload(
        db,
        account_id=account.account_id,
        org_id=org.org_id,
        data_domain=org.data_domain,
        country=org.country,
        data=data,
    )


def list_uploads_for_account(db: Session, account: Account):
    if account.role == AccountRole.ADMIN:
        return list_uploads(db)
    if account.role == AccountRole.ORG and account.org_id:
        return list_uploads_by_org(db, account.org_id)
    return []


def admin_update_upload(db: Session, upload_id: int, data: UploadUpdateStatus):
    upload = get_upload_by_id(db, upload_id)
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    return update_upload_status(db, upload, data)
