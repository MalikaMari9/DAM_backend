from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import require_admin
from app.controllers.file_controller import save_application_file
from app.repositories.org_application_file_repo import list_org_application_files
from app.schemas.org_application_file_schema import OrgApplicationFileRead

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/applications/{application_id}", response_model=list[OrgApplicationFileRead])
def list_application_files_route(
    application_id: int,
    db: Session = Depends(get_db),
    _account=Depends(require_admin),
):
    return list_org_application_files(db, application_id)


@router.post("/applications/{application_id}", response_model=OrgApplicationFileRead)
def upload_application_file_route(
    application_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _account=Depends(require_admin),
):
    return save_application_file(db, application_id, file)
