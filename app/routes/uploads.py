from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import get_current_account, require_admin, require_org
from app.controllers.upload_controller import (
    create_org_upload,
    list_uploads_for_account,
    admin_update_upload,
)
from app.schemas.upload_schema import UploadCreate, UploadRead, UploadUpdateStatus

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadRead)
def create_upload_route(
    payload: UploadCreate,
    db: Session = Depends(get_db),
    account=Depends(require_org),
):
    return create_org_upload(db, account, payload)


@router.get("", response_model=list[UploadRead])
def list_uploads_route(
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    return list_uploads_for_account(db, account)


@router.patch("/{upload_id}", response_model=UploadRead)
def update_upload_route(
    upload_id: int,
    payload: UploadUpdateStatus,
    db: Session = Depends(get_db),
    _account=Depends(require_admin),
):
    return admin_update_upload(db, upload_id, payload)
