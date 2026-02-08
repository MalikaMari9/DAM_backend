from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timezone
import secrets
import string
from app.models.enums import ApplicationStatus, AccountRole
from app.schemas.org_application_schema import OrgApplicationCreate, OrgApplicationUpdate
from app.schemas.org_schema import OrgCreate
from app.schemas.account_schema import AccountCreate
from app.repositories.org_application_repo import (
    create_org_application,
    get_org_application_by_id,
    list_org_applications,
    update_org_application,
)
from app.repositories.org_repo import create_org
from app.repositories.account_repo import create_account, get_account_by_email
from app.core.security import hash_password
from app.core.email import send_email


def _generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _send_submission_email(to_email: str, org_name: str):
    subject = "AirHealth: Organization Registration Received"
    html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6;">
      <h2>Registration received</h2>
      <p>Hello {org_name},</p>
      <p>We have received your organization registration request. Our team will review it and get back to you soon.</p>
      <p>Thank you,<br/>AirHealth Team</p>
    </div>
    """
    send_email(to_email, subject, html)


def _send_approval_email(to_email: str, org_name: str, password: str):
    subject = "AirHealth: Your Organization Has Been Approved"
    html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6;">
      <h2>Approval successful</h2>
      <p>Hello {org_name},</p>
      <p>Your organization has been approved. An account has been created for you.</p>
      <p><strong>Login email:</strong> {to_email}<br/>
         <strong>Temporary password:</strong> {password}</p>
      <p>Please log in and change your password as soon as possible.</p>
      <p>Thank you,<br/>AirHealth Team</p>
    </div>
    """
    send_email(to_email, subject, html)


def _send_rejection_email(to_email: str, org_name: str):
    subject = "AirHealth: Organization Application Update"
    html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6;">
      <h2>Application update</h2>
      <p>Hello {org_name},</p>
      <p>We reviewed your application and unfortunately cannot approve it at this time. The submitted data is insufficient or incomplete.</p>
      <p>You are welcome to resubmit with additional information.</p>
      <p>Thank you,<br/>AirHealth Team</p>
    </div>
    """
    send_email(to_email, subject, html)


def _send_to_all_recipients(official_email: str, contact_email: str | None, subject_fn):
    recipients = {official_email}
    if contact_email:
        recipients.add(contact_email)
    for email in recipients:
        subject_fn(email)


def submit_application(db: Session, data: OrgApplicationCreate):
    app = create_org_application(db, data)
    try:
        def _send(to_email: str):
            _send_submission_email(to_email, data.org_name)

        _send_to_all_recipients(data.official_email, data.contact_email, _send)
    except Exception:
        pass
    return app


def get_application(db: Session, application_id: int):
    app = get_org_application_by_id(db, application_id)
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return app


def list_applications(db: Session, status: str | None = None):
    return list_org_applications(db, status=status)


def review_application(db: Session, application_id: int, data: OrgApplicationUpdate):
    app = get_org_application_by_id(db, application_id)
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if data.status == ApplicationStatus.APPROVED:
        existing = get_account_by_email(db, app.official_email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists for this email")

        org_payload = OrgCreate(
            org_name=app.org_name,
            org_type=app.org_type,
            data_domain=app.data_domain,
            country=app.country,
            address_detail=app.address_detail,
            official_email=app.official_email,
            website=app.website,
            contact_name=app.contact_name,
            contact_email=app.contact_email,
        )
        org = create_org(db, org_payload)

        temp_password = _generate_password()
        account_payload = AccountCreate(
            email=app.official_email,
            password=temp_password,
            role=AccountRole.ORG,
            org_id=org.org_id,
            is_active=True,
        )
        create_account(db, account_payload, hash_password(temp_password))

        try:
            def _send(to_email: str):
                _send_approval_email(to_email, app.org_name, temp_password)

            _send_to_all_recipients(app.official_email, app.contact_email, _send)
        except Exception:
            pass
    elif data.status == ApplicationStatus.REJECTED:
        try:
            def _send(to_email: str):
                _send_rejection_email(to_email, app.org_name)

            _send_to_all_recipients(app.official_email, app.contact_email, _send)
        except Exception:
            pass

    updates = data.dict(exclude_unset=True)
    for k, v in updates.items():
        setattr(app, k, v)
    if data.status in (ApplicationStatus.APPROVED, ApplicationStatus.REJECTED):
        app.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(app)
    return app
