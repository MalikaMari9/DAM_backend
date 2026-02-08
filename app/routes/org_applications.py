from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import require_admin
from app.models.enums import ApplicationStatus
from app.controllers.org_application_controller import (
    submit_application,
    get_application,
    list_applications,
    review_application,
)
from app.schemas.org_application_schema import (
    OrgApplicationCreate,
    OrgApplicationRead,
    OrgApplicationUpdate,
)

router = APIRouter(prefix="/org-applications", tags=["org-applications"])


@router.post("", response_model=OrgApplicationRead)
def submit_application_route(payload: OrgApplicationCreate, db: Session = Depends(get_db)):
    return submit_application(db, payload)


@router.get("", response_model=list[OrgApplicationRead])
def list_applications_route(
    status: ApplicationStatus | None = Query(default=None),
    db: Session = Depends(get_db),
    _account=Depends(require_admin),
):
    return list_applications(db, status=status)


@router.get("/{application_id}", response_model=OrgApplicationRead)
def get_application_route(
    application_id: int,
    db: Session = Depends(get_db),
    _account=Depends(require_admin),
):
    return get_application(db, application_id)


@router.patch("/{application_id}", response_model=OrgApplicationRead)
def review_application_route(
    application_id: int,
    payload: OrgApplicationUpdate,
    db: Session = Depends(get_db),
    _account=Depends(require_admin),
):
    return review_application(db, application_id, payload)
