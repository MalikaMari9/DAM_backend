from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.org_model import Org
from app.schemas.org_schema import OrgCreate, OrgUpdate


def get_org_by_id(db: Session, org_id: int) -> Org | None:
    stmt = select(Org).where(Org.org_id == org_id)
    return db.execute(stmt).scalars().first()


def get_orgs(db: Session) -> list[Org]:
    stmt = select(Org)
    return list(db.execute(stmt).scalars().all())


def create_org(db: Session, data: OrgCreate) -> Org:
    org = Org(**data.dict())
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def update_org(db: Session, org: Org, data: OrgUpdate) -> Org:
    updates = data.dict(exclude_unset=True)
    for k, v in updates.items():
        setattr(org, k, v)
    db.commit()
    db.refresh(org)
    return org