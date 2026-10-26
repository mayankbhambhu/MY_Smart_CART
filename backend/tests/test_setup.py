"""Deployment settings, the demo accounts and the admin command line."""

from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import Settings, get_settings
from app.core.types import utcnow
from app.main import _housekeeping, mount_frontend
from app.manage import set_role
from app.models import OtpRequest, Store, User
from app.seed import disable_demo_staff, grant_admins
from tests.conftest import DEMO_CUSTOMER, STAFF_SECTOR_29

STRONG_SECRET = "x" * 48


@pytest.mark.parametrize(
    ("overrides", "complaint"),
    [
        ({"sms_provider": "msg91"}, "MSG91_AUTH_KEY"),
        ({"sms_provider": "twilio", "twilio_account_sid": "AC1"}, "TWILIO_AUTH_TOKEN"),
        ({"razorpay_key_id": "rzp_test_abc"}, "RAZORPAY_KEY_SECRET"),
        ({"environment": "demo"}, "SECRET_KEY"),
        ({"environment": "production", "secret_key": STRONG_SECRET}, "SMS_PROVIDER"),
    ],
)
def test_unsafe_settings_stop_the_app_from_starting(overrides, complaint):
    with pytest.raises(RuntimeError, match=complaint):
        Settings(_env_file=None, **overrides).validate_settings()


def test_production_settings():
    settings = Settings(
        _env_file=None,
        environment="production",
        secret_key=STRONG_SECRET,
        sms_provider="msg91",
        msg91_auth_key="key",
        msg91_otp_template_id="template",
        database_url="postgres://smartcart:pw@db.internal:5432/smartcart",
    )
    settings.validate_settings()
    assert settings.payment_provider is None  # no simulator for real customers
    assert settings.database_url == "postgresql+psycopg://smartcart:pw@db.internal:5432/smartcart"
    with_keys = settings.model_copy(update={"razorpay_key_id": "rzp_live_x", "razorpay_key_secret": "s"})
    assert with_keys.payment_provider == "razorpay"


def test_demo_staff_logins_are_closed_once_sms_is_real(db, monkeypatch):
    staff = db.scalars(select(User).where(User.phone == STAFF_SECTOR_29)).one()
    assert staff.role == "staff"
    monkeypatch.setattr(get_settings(), "sms_provider", "msg91")
    disable_demo_staff(db)
    db.refresh(staff)
    assert staff.role == "customer" and staff.store_id is None


def test_set_role_command(db):
    assert "is now staff at" in set_role("+91 98111 22233", "staff", "dlf-phase-3")
    db.expire_all()
    user = db.scalars(select(User).where(User.phone == "9811122233")).one()
    store = db.get(Store, user.store_id)
    assert user.role == "staff" and store.slug == "dlf-phase-3"

    set_role("9811122233", "customer", None)
    db.expire_all()
    assert db.scalars(select(User.role).where(User.phone == "9811122233")).one() == "customer"

    with pytest.raises(SystemExit, match="Stores:"):
        set_role("9811122233", "staff", "nowhere")
    with pytest.raises(SystemExit, match="need --store"):
        set_role("9811122233", "staff", None)
    with pytest.raises(SystemExit, match="valid"):
        set_role("12345", "admin", None)


def test_admin_phones_setting(db):
    grant_admins(db, f" +91 98111 22233 , not-a-number,{DEMO_CUSTOMER}")
    roles = dict(db.execute(select(User.phone, User.role).where(User.role == "admin")).all())
    assert roles["9811122233"] == "admin" and roles[DEMO_CUSTOMER] == "admin"


def test_housekeeping_clears_old_login_codes(db):
    now = utcnow()
    for age in (timedelta(minutes=5), timedelta(days=2)):
        db.add(OtpRequest(phone="9811122233", code_hash="x", created_at=now - age, expires_at=now))
    db.commit()
    _housekeeping()
    assert db.scalar(select(func.count()).select_from(OtpRequest)) == 1


def test_built_web_app_is_served_for_get_and_head(tmp_path, client):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>Smart Cart</title>")
    (tmp_path / "favicon.svg").write_text("<svg/>")
    (tmp_path.parent / "secret.txt").write_text("nope")
    app = FastAPI()
    mount_frontend(app, tmp_path)
    web = TestClient(app)

    for path in ("/", "/orders/12", "/favicon.svg"):
        assert web.get(path).status_code == 200
        assert web.head(path).status_code == 200
    assert "Smart Cart" in web.get("/orders/12").text  # client-side routes get the app
    assert web.get("/api/nope").status_code == 404
    assert "nope" not in web.get("/../secret.txt").text
    assert client.head("/api/health").status_code == 200
