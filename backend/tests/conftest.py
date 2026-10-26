import os
import tempfile

# Configure the app before it is imported anywhere.
_tmp_dir = tempfile.mkdtemp(prefix="smartcart-tests-")
# Set TEST_DATABASE_URL (e.g. postgresql://localhost/smartcart_test) to run against PostgreSQL.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_tmp_dir}/test.db"
os.environ["ENVIRONMENT"] = "test"
os.environ["AUTO_SEED"] = "false"
os.environ["SIMULATE_ORDER_PROGRESS"] = "false"
os.environ["FRONTEND_DIST"] = os.path.join(_tmp_dir, "no-frontend")
# Never reach a real SMS gateway or Razorpay from tests, whatever a local .env says.
os.environ["SMS_PROVIDER"] = "console"
os.environ["SIMULATED_PAYMENTS"] = "true"
for _name in ("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET", "WEBOTP_DOMAIN"):
    os.environ[_name] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Address, Product, StoreInventory, User  # noqa: E402
from app.seed import seed_database  # noqa: E402

DEMO_CUSTOMER = "9876543210"
STAFF_SECTOR_29 = "9000000001"
STAFF_DLF = "9000000002"


@pytest.fixture
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed_database(session)
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client(db):
    with TestClient(create_app()) as test_client:
        yield test_client


def login(client: TestClient, phone: str) -> dict[str, str]:
    otp = client.post("/api/auth/otp/request", json={"phone": phone}).json()["dev_otp"]
    token = client.post("/api/auth/otp/verify", json={"phone": phone, "otp": otp}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def customer(client) -> dict[str, str]:
    return login(client, DEMO_CUSTOMER)


@pytest.fixture
def staff(client) -> dict[str, str]:
    return login(client, STAFF_SECTOR_29)


def pay(client: TestClient, headers: dict[str, str], order_id: int, outcome: str = "success") -> dict:
    """Pays for an online order with the built-in simulator (tests run without Razorpay keys)."""
    session = client.post(f"/api/payments/orders/{order_id}/session", headers=headers)
    assert session.status_code == 200, session.text
    assert session.json()["provider"] == "simulated"
    paid = client.post(
        f"/api/payments/orders/{order_id}/simulate", headers=headers, json={"outcome": outcome}
    )
    assert paid.status_code == 200, paid.text
    return paid.json()


def find_product(db, name: str, unit: str) -> Product:
    return db.scalars(select(Product).where(Product.name == name, Product.unit_label == unit)).one()


def stock_of(db, store_id: int, product_id: int) -> int:
    db.expire_all()
    return db.scalar(
        select(StoreInventory.stock).where(
            StoreInventory.store_id == store_id, StoreInventory.product_id == product_id
        )
    )


def home_address_id(db) -> int:
    user = db.scalars(select(User).where(User.phone == DEMO_CUSTOMER)).one()
    return db.scalars(select(Address.id).where(Address.user_id == user.id)).first()


def first_slot(client, store_id: int = 1) -> str:
    days = client.get(f"/api/stores/{store_id}/pickup-slots").json()
    return next(slot["start"] for day in days for slot in day["slots"] if slot["available"])
