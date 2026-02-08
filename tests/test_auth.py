from app.core.security import decode_access_token, hash_password
from app.models.account_model import Account
from app.models.enums import AccountRole


def seed_account(db):
    account = Account(
        account_id=1,
        email="admin@example.com",
        password_hash=hash_password("correct-password"),
        role=AccountRole.ADMIN,
        org_id=None,
        is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def test_login_success(client, db_session):
    account = seed_account(db_session)
    resp = client.post(
        "/auth/login",
        json={"email": account.email, "password": "correct-password"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    payload = decode_access_token(body["access_token"])
    assert payload["sub"] == str(account.account_id)


def test_login_invalid_password(client, db_session):
    account = seed_account(db_session)
    resp = client.post(
        "/auth/login",
        json={"email": account.email, "password": "wrong-password"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


def test_login_unknown_email(client):
    resp = client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": "whatever"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"
