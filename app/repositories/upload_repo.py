from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.upload_model import Upload
from app.schemas.upload_schema import UploadCreate, UploadUpdateStatus


def create_upload(
    db: Session,
    account_id: int,
    org_id: int,
    data_domain,
    country: str,
    data: UploadCreate,
) -> Upload:
    upload = Upload(
        account_id=account_id,
        org_id=org_id,
        data_domain=data_domain,
        mongo_collection=data.mongo_collection,
        mongo_ref_id=data.mongo_ref_id,
        country=country,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload


def get_upload_by_id(db: Session, upload_id: int) -> Upload | None:
    stmt = select(Upload).where(Upload.upload_id == upload_id)
    return db.execute(stmt).scalars().first()


def list_uploads(db: Session) -> list[Upload]:
    stmt = select(Upload)
    return list(db.execute(stmt).scalars().all())


def list_uploads_by_org(db: Session, org_id: int) -> list[Upload]:
    stmt = select(Upload).where(Upload.org_id == org_id)
    return list(db.execute(stmt).scalars().all())


def update_upload_status(db: Session, upload: Upload, data: UploadUpdateStatus) -> Upload:
    upload.status = data.status
    upload.error_message = data.error_message
    db.commit()
    db.refresh(upload)
    return upload
