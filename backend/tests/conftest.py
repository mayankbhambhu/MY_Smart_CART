import os
import tempfile

# Configure the app before it is imported anywhere.
_tmp_dir = tempfile.mkdtemp(prefix="smartcart-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_dir}/test.db"
os.environ["AUTO_SEED"] = "false"
os.environ["SIMULATE_ORDER_PROGRESS"] = "false"
os.environ["FRONTEND_DIST"] = os.path.join(_tmp_dir, "no-frontend")
os.environ["OTP_DEV_MODE"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.main import create_app  # noqa: E402
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
