from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.enums import AccountRole
from app.schemas.admin_schema import AdminCreate, OrgAccountCreate
from app.schemas.account_schema import AccountCreate
from app.schemas.org_schema import OrgCreate
from app.repositories.account_repo import create_account, get_account_by_email
from app.repositories.org_repo import create_org
from app.core.security import hash_password
from app.core.email import send_email
from app.controllers.auth_controller import generate_temp_password


def _send_new_account_email(to_email: str, temp_password: str, label: str):
    subject = "AirHealth: Your Account Has Been Created"
    html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6;">
      <h2>Account created</h2>
      <p>Your {label} account has been created.</p>
      <p><strong>Login email:</strong> {to_email}<br/>
         <strong>Temporary password:</strong> {temp_password}</p>
      <p>Please log in and change your password as soon as possible.</p>
      <p>Thank you,<br/>AirHealth Team</p>
    </div>
    """
    send_email(to_email, subject, html)


def create_admin_account(db: Session, data: AdminCreate):
    existing = get_account_by_email(db, data.email)
    if existing:
        return {"status": "exists"}

    temp_password = generate_temp_password()
    account_payload = AccountCreate(
        email=data.email,
        password=temp_password,
        role=AccountRole.ADMIN,
        org_id=None,
        is_active=True,
    )
    create_account(db, account_payload, hash_password(temp_password))

    try:
        _send_new_account_email(data.email, temp_password, "admin")
    except Exception:
        pass

    return {"status": "ok"}


def create_org_account(db: Session, data: OrgAccountCreate):
    existing = get_account_by_email(db, data.official_email)
    if existing:
        return {"status": "exists"}

    org_payload = OrgCreate(
        org_name=data.org_name,
        org_type=data.org_type,
        data_domain=data.data_domain,
        country=data.country,
        address_detail=data.address_detail,
        official_email=data.official_email,
        website=None,
        contact_name=data.contact_name,
        contact_email=data.contact_email,
    )
    org = create_org(db, org_payload)

    temp_password = generate_temp_password()
    account_payload = AccountCreate(
        email=data.official_email,
        password=temp_password,
        role=AccountRole.ORG,
        org_id=org.org_id,
        is_active=True,
    )
    create_account(db, account_payload, hash_password(temp_password))

    try:
        _send_new_account_email(data.official_email, temp_password, "organization")
    except Exception:
        pass

    return {"status": "ok"}
