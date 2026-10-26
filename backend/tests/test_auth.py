from datetime import timedelta

from sqlalchemy import update

from app.core.types import utcnow
from app.models import OtpRequest
from tests.conftest import login


def test_otp_login_creates_account_and_returns_token(client):
    sent = client.post("/api/auth/otp/request", json={"phone": "+91 98111 22233"})
    assert sent.status_code == 200
    body = sent.json()
    assert body["phone"] == "9811122233"
    assert len(body["dev_otp"]) == 6

    verified = client.post("/api/auth/otp/verify", json={"phone": "9811122233", "otp": body["dev_otp"]})
    assert verified.status_code == 200
    data = verified.json()
    assert data["is_new_user"] is True
    assert data["user"]["role"] == "customer"

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.json()["phone"] == "9811122233"


def test_otp_cannot_be_reused_and_resend_has_cooldown(client, db):
    otp = client.post("/api/auth/otp/request", json={"phone": "9811122233"}).json()["dev_otp"]
    assert client.post("/api/auth/otp/verify", json={"phone": "9811122233", "otp": otp}).status_code == 200
    again = client.post("/api/auth/otp/verify", json={"phone": "9811122233", "otp": otp})
    assert again.status_code == 400

    too_soon = client.post("/api/auth/otp/request", json={"phone": "9811122233"})
    assert too_soon.status_code == 429
    assert too_soon.json()["details"]["retry_after"] > 0

    db.execute(update(OtpRequest).values(created_at=utcnow() - timedelta(minutes=1)))
    db.commit()
    otp = client.post("/api/auth/otp/request", json={"phone": "9811122233"}).json()["dev_otp"]
    second = client.post("/api/auth/otp/verify", json={"phone": "9811122233", "otp": otp}).json()
    assert second["is_new_user"] is False


def test_wrong_otp_is_rejected_and_attempts_are_limited(client):
    otp = client.post("/api/auth/otp/request", json={"phone": "9811122233"}).json()["dev_otp"]
    wrong = "000000" if otp != "000000" else "111111"
    for _ in range(5):
        assert (
            client.post("/api/auth/otp/verify", json={"phone": "9811122233", "otp": wrong}).status_code == 400
        )
    locked = client.post("/api/auth/otp/verify", json={"phone": "9811122233", "otp": otp})
    assert locked.status_code == 429


def test_invalid_phone_numbers_are_rejected(client):
    for phone in ["12345", "5123456789", "98765432100"]:
        assert client.post("/api/auth/otp/request", json={"phone": phone}).status_code == 422


def test_protected_routes_need_a_valid_token(client):
    assert client.get("/api/orders").status_code == 401
    bad = client.get("/api/orders", headers={"Authorization": "Bearer not-a-token"})
    assert bad.status_code == 401


def test_profile_update(client):
    headers = login(client, "9811122233")
    res = client.patch(
        "/api/auth/me", json={"name": "  Priya  ", "email": "priya@example.com"}, headers=headers
    )
    assert res.json()["name"] == "Priya"
    assert client.patch("/api/auth/me", json={"email": "nope"}, headers=headers).status_code == 422
