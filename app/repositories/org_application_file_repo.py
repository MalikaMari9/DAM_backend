from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.org_application_file_model import OrgApplicationFile
from app.schemas.org_application_file_schema import OrgApplicationFileCreate


def create_org_application_file(db: Session, data: OrgApplicationFileCreate) -> OrgApplicationFile:
    f = OrgApplicationFile(**data.dict())
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


def list_org_application_files(db: Session, application_id: int) -> list[OrgApplicationFile]:
    stmt = select(OrgApplicationFile).where(OrgApplicationFile.application_id == application_id)
    return list(db.execute(stmt).scalars().all())