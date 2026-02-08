from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.org_application_model import OrgApplication
from app.schemas.org_application_schema import OrgApplicationCreate, OrgApplicationUpdate
from app.models.enums import ApplicationStatus


def create_org_application(db: Session, data: OrgApplicationCreate) -> OrgApplication:
    app = OrgApplication(**data.dict())
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


def get_org_application_by_id(db: Session, application_id: int) -> OrgApplication | None:
    stmt = select(OrgApplication).where(OrgApplication.application_id == application_id)
    return db.execute(stmt).scalars().first()


def list_org_applications(db: Session, status: ApplicationStatus | None = None) -> list[OrgApplication]:
    stmt = select(OrgApplication)
    if status:
        stmt = stmt.where(OrgApplication.status == status)
    return list(db.execute(stmt).scalars().all())


def update_org_application(db: Session, app: OrgApplication, data: OrgApplicationUpdate) -> OrgApplication:
    updates = data.dict(exclude_unset=True)
    for k, v in updates.items():
        setattr(app, k, v)
    db.commit()
    db.refresh(app)
    return app
