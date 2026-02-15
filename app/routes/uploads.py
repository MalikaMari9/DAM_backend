from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import get_current_account, require_admin, require_org
from app.controllers.upload_controller import (
    create_org_upload,
    list_uploads_for_account,
    admin_update_upload,
    create_health_csv_validation,
    confirm_health_csv_upload,
    list_csv_dupes,
    create_health_record_upload,
    create_pollution_csv_validation,
    confirm_pollution_csv_upload,
    list_pollution_csv_dupes,
    create_pollution_record_upload,
    list_upload_records,
    update_upload_record,
    delete_upload_with_records,
)
from app.schemas.upload_schema import (
    UploadCreate,
    UploadRead,
    UploadUpdateStatus,
    HealthIMHERecordManual,
    PollutionOpenAQRecordManual,
    UploadRecordList,
    UploadRecordUpdate,
)

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadRead)
def create_upload_route(
    payload: UploadCreate,
    db: Session = Depends(get_db),
    account=Depends(require_org),
):
    return create_org_upload(db, account, payload)


@router.post("/health/csv/validate")
async def upload_health_csv_validate(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    account=Depends(require_org),
):
    if file.filename and not any(file.filename.lower().endswith(ext) for ext in (".csv", ".xlsx", ".xls", ".json")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV, Excel (.xlsx/.xls), or JSON files are supported for health uploads.",
        )
    file_bytes = await file.read()
    return create_health_csv_validation(
        db,
        account,
        file_bytes=file_bytes,
        filename=file.filename or "health.csv",
    )


@router.post("/pollution/csv/validate")
async def upload_pollution_csv_validate(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    account=Depends(require_org),
):
    if file.filename and not any(file.filename.lower().endswith(ext) for ext in (".csv", ".xlsx", ".xls", ".json")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV, Excel (.xlsx/.xls), or JSON files are supported for pollution uploads.",
        )
    file_bytes = await file.read()
    return create_pollution_csv_validation(
        db,
        account,
        file_bytes=file_bytes,
        filename=file.filename or "pollution.csv",
    )


@router.post("/health/csv/confirm", response_model=UploadRead)
def upload_health_csv_confirm(
    token: str,
    db: Session = Depends(get_db),
    account=Depends(require_org),
):
    return confirm_health_csv_upload(db, account, token)


@router.post("/pollution/csv/confirm", response_model=UploadRead)
def upload_pollution_csv_confirm(
    token: str,
    db: Session = Depends(get_db),
    account=Depends(require_org),
):
    return confirm_pollution_csv_upload(db, account, token)


@router.get("/health/csv/dupes")
def upload_health_csv_dupes(
    token: str,
    limit: int = 5,
    offset: int = 0,
    db: Session = Depends(get_db),
    account=Depends(require_org),
):
    return list_csv_dupes(db, account, token, limit=limit, offset=offset)


@router.get("/pollution/csv/dupes")
def upload_pollution_csv_dupes(
    token: str,
    limit: int = 5,
    offset: int = 0,
    db: Session = Depends(get_db),
    account=Depends(require_org),
):
    return list_pollution_csv_dupes(db, account, token, limit=limit, offset=offset)


@router.post("/health/record", response_model=UploadRead)
def upload_health_record(
    payload: HealthIMHERecordManual,
    db: Session = Depends(get_db),
    account=Depends(require_org),
):
    return create_health_record_upload(db, account, payload)


@router.post("/pollution/record", response_model=UploadRead)
def upload_pollution_record(
    payload: PollutionOpenAQRecordManual,
    db: Session = Depends(get_db),
    account=Depends(require_org),
):
    return create_pollution_record_upload(db, account, payload)


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


@router.get("/{upload_id}/records", response_model=UploadRecordList)
def list_upload_records_route(
    upload_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    return list_upload_records(db, account, upload_id, limit=limit, offset=offset)


@router.patch("/{upload_id}/records/{record_id}")
def update_upload_record_route(
    upload_id: int,
    record_id: str,
    payload: UploadRecordUpdate,
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    return update_upload_record(db, account, upload_id, record_id, payload)


@router.delete("/{upload_id}")
def delete_upload_route(
    upload_id: int,
    db: Session = Depends(get_db),
    account=Depends(get_current_account),
):
    return delete_upload_with_records(db, account, upload_id)
