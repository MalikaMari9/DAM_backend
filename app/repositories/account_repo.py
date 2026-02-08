from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.account_model import Account
from app.schemas.account_schema import AccountCreate


def get_account_by_email(db: Session, email: str) -> Account | None:
    stmt = select(Account).where(Account.email.ilike(email))
    return db.execute(stmt).scalars().first()


def get_account_by_id(db: Session, account_id: int) -> Account | None:
    stmt = select(Account).where(Account.account_id == account_id)
    return db.execute(stmt).scalars().first()


def create_account(db: Session, data: AccountCreate, password_hash: str) -> Account:
    account = Account(
        email=data.email,
        password_hash=password_hash,
        role=data.role,
        org_id=data.org_id,
        is_active=data.is_active,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account