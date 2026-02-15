from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.account_model import Account
from app.models.enums import AccountRole, DataDomain, OrgStatus, OrgType
from app.models.org_model import Org


SEED_PASSWORD = "Test12345"

SEED_ORGS = [
    {
        "org_name": "Myanmar Clean Air Initiative",
        "org_type": OrgType.WEATHER_STATION,
        "data_domain": DataDomain.POLLUTION,
        "country": "Myanmar",
        "address_detail": "No. 12 Pyay Road, Yangon",
        "official_email": "contact@mycleanair.com",
        "website": "https://mycleanair.com",
        "contact_name": "Aye Chan",
        "contact_email": "aye.chan@mycleanair.com",
        "account_email": "myanmar.pollution@seed.example.com",
    },
    {
        "org_name": "Tokyo Air Quality Lab",
        "org_type": OrgType.WEATHER_STATION,
        "data_domain": DataDomain.POLLUTION,
        "country": "Japan",
        "address_detail": "1-1 Chiyoda, Tokyo",
        "official_email": "info@tokyoair.com",
        "website": "https://tokyoair.com",
        "contact_name": "Haruka Sato",
        "contact_email": "haruka.sato@tokyoair.com",
        "account_email": "japan.pollution@seed.example.com",
    },
    {
        "org_name": "Osaka Health Research Center",
        "org_type": OrgType.RESEARCH_INSTITUTION,
        "data_domain": DataDomain.HEALTH,
        "country": "Japan",
        "address_detail": "2-2 Kita, Osaka",
        "official_email": "hello@osakahealth.com",
        "website": "https://osakahealth.com",
        "contact_name": "Kenji Mori",
        "contact_email": "kenji.mori@osakahealth.com",
        "account_email": "japan.health@seed.example.com",
    },
    {
        "org_name": "Beijing Pollution Monitoring Unit",
        "org_type": OrgType.GOVERNMENT,
        "data_domain": DataDomain.POLLUTION,
        "country": "China",
        "address_detail": "100 Chang'an Avenue, Beijing",
        "official_email": "contact@bjmonitor.com",
        "website": "https://bjmonitor.com",
        "contact_name": "Li Wei",
        "contact_email": "li.wei@bjmonitor.com",
        "account_email": "china.pollution@seed.example.com",
    },
    {
        "org_name": "California Health Alliance",
        "org_type": OrgType.HOSPITAL,
        "data_domain": DataDomain.HEALTH,
        "country": "United States",
        "address_detail": "500 Market Street, San Francisco, CA",
        "official_email": "support@calhealth.com",
        "website": "https://calhealth.com",
        "contact_name": "Maria Gomez",
        "contact_email": "maria.gomez@calhealth.com",
        "account_email": "usa.health@seed.example.com",
    },
]


def seed_organizations(db: Session) -> list[Org]:
    created_orgs: list[Org] = []
    password_hash = hash_password(SEED_PASSWORD)

    for item in SEED_ORGS:
        existing_org = db.query(Org).filter(Org.org_name == item["org_name"]).first()
        existing_account = db.query(Account).filter(Account.email == item["account_email"]).first()
        if existing_org or existing_account:
            continue

        org = Org(
            org_name=item["org_name"],
            org_type=item["org_type"],
            data_domain=item["data_domain"],
            country=item["country"],
            address_detail=item["address_detail"],
            official_email=item["official_email"],
            website=item["website"],
            contact_name=item["contact_name"],
            contact_email=item["contact_email"],
            status=OrgStatus.ACTIVE,
        )
        db.add(org)
        db.flush()

        account = Account(
            email=item["account_email"],
            password_hash=password_hash,
            role=AccountRole.ORG,
            org_id=org.org_id,
            is_active=True,
        )
        db.add(account)
        created_orgs.append(org)

    db.commit()
    return created_orgs


def run_seed() -> None:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not set")
    db = SessionLocal()
    try:
        seed_organizations(db)
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
