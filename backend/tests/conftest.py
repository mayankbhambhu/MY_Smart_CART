import os
import tempfile

# Point the app at a throwaway database before it is imported.
_db_dir = tempfile.mkdtemp()
os.environ["SMARTCART_DATABASE_URL"] = f"sqlite:///{_db_dir}/test.db"
os.environ["SMARTCART_DEV_MODE"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import STAFF_PHONE, seed  # noqa: E402

# Koramangala store (open 24h) and a spot ~1 km from it.
STORE_ID = 1
HOME = {"lat": 12.9300, "lng": 77.6200}


@pytest.fixture
def db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        seed(session)
        yield session


@pytest.fixture
def client(db):
    with TestClient(app) as c:
        yield c


def login(client: TestClient, phone: str) -> dict[str, str]:
    otp = client.post("/api/auth/otp/request", json={"phone": phone}).json()["dev_otp"]
    token = client.post("/api/auth/otp/verify", json={"phone": phone, "otp": otp}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def customer(client):
    return login(client, "9876543210")


@pytest.fixture
def staff(client):
    return login(client, STAFF_PHONE)


@pytest.fixture
def address_id(client, customer):
    body = {"label": "Home", "line1": "12, 5th Cross", "city": "Bengaluru", "pincode": "560034", **HOME}
    return client.post("/api/addresses", json=body, headers=customer).json()["id"]


def in_stock_products(client: TestClient, store_id: int = STORE_ID, count: int = 3) -> list[dict]:
    products = client.get("/api/products", params={"store_id": store_id, "limit": 200}).json()
    return [p for p in products if p["in_stock"] and p["stock"] >= 5][:count]
