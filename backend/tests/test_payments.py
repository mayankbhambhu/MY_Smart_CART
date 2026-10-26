import base64
import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timedelta

import httpx2
import pytest
from sqlalchemy import update

from app.core.config import get_settings
from app.core.types import utcnow
from app.models import Order
from app.services import outbound
from app.services.payments import expire_unpaid_orders
from tests.conftest import find_product, first_slot, home_address_id, pay, stock_of

KEY_ID = "rzp_test_1DP5mmOlF5G5ag"
KEY_SECRET = "test-key-secret"
WEBHOOK_SECRET = "test-webhook-secret"


class FakeRazorpay:
    """Just enough of Razorpay's REST API (orders, payments, capture, refunds) to run our client
    against. `pay()` plays the customer completing Checkout."""

    def __init__(self):
        self.orders: dict[str, dict] = {}
        self.payments: dict[str, dict] = {}
        self.refunds: list[dict] = []
        self.requests: list[httpx2.Request] = []
        self.failing: dict[str, int] = {}  # "METHOD /path-prefix" -> HTTP status to answer with

    def pay(self, order_id: str, *, status: str = "captured", amount: int | None = None, **extra) -> str:
        payment_id = f"pay_{secrets.token_hex(7)}"
        self.payments[payment_id] = {
            "id": payment_id,
            "entity": "payment",
            "order_id": order_id,
            "amount": self.orders[order_id]["amount"] if amount is None else amount,
            "currency": "INR",
            "status": status,
            "method": "upi",
            **extra,
        }
        return payment_id

    def calls(self, method: str, pattern: str) -> list[httpx2.Request]:
        return [r for r in self.requests if r.method == method and re.fullmatch(pattern, r.url.path)]

    def handler(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        path = request.url.path.removeprefix("/v1")
        call = f"{request.method} {path}"
        for prefix, status in self.failing.items():
            if call.startswith(prefix):
                return _error(status, "Something went wrong at the gateway")
        body = json.loads(request.content) if request.content else {}

        if call == "POST /orders":
            order_id = f"order_{secrets.token_hex(7)}"
            self.orders[order_id] = {"id": order_id, "entity": "order", "status": "created", **body}
            return httpx2.Response(200, json=self.orders[order_id])
        if match := re.fullmatch(r"GET /orders/(\w+)/payments", call):
            items = [p for p in self.payments.values() if p["order_id"] == match[1]]
            return httpx2.Response(200, json={"entity": "collection", "count": len(items), "items": items})
        if match := re.fullmatch(r"(GET|POST) /payments/(\w+)(/capture|/refund)?", call):
            payment = self.payments.get(match[2])
            if payment is None:
                return _error(400, "The id provided does not exist")
            if match[3] == "/capture":
                if payment["status"] != "authorized" or body["amount"] != payment["amount"]:
                    return _error(400, "This payment has already been captured")
                payment["status"] = "captured"
            if match[3] == "/refund":
                refund = {"id": f"rfnd_{secrets.token_hex(7)}", "payment_id": payment["id"], **body}
                self.refunds.append(refund)
                return httpx2.Response(200, json=refund)
            return httpx2.Response(200, json=payment)
        return _error(404, "The requested URL was not found on the server.")


def _error(status: int, description: str) -> httpx2.Response:
    return httpx2.Response(status, json={"error": {"code": "BAD_REQUEST_ERROR", "description": description}})


@pytest.fixture
def razorpay(monkeypatch) -> FakeRazorpay:
    settings = get_settings()
    monkeypatch.setattr(settings, "razorpay_key_id", KEY_ID)
    monkeypatch.setattr(settings, "razorpay_key_secret", KEY_SECRET)
    monkeypatch.setattr(settings, "razorpay_webhook_secret", WEBHOOK_SECRET)
    fake = FakeRazorpay()
    monkeypatch.setattr(
        outbound, "client", lambda: httpx2.Client(transport=httpx2.MockTransport(fake.handler))
    )
    return fake


def _checkout_signature(order_id: str, payment_id: str) -> str:
    return hmac.new(KEY_SECRET.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()


def _place(client, db, headers, *, kind: str = "delivery", quantity: int = 2) -> dict:
    milk = find_product(db, "Amul Taaza Toned Milk", "500 ml")
    body = {
        "store_id": 1,
        "fulfillment_type": kind,
        "payment_method": "online",
        "items": [{"product_id": milk.id, "quantity": quantity}],
    }
    if kind == "delivery":
        body["address_id"] = home_address_id(db)
    else:
        body["pickup_slot_start"] = first_slot(client)
    res = client.post("/api/orders", headers=headers, json=body)
    assert res.status_code == 201, res.text
    return res.json()


def _instore_bill(client, db, headers) -> dict:
    bread = find_product(db, "Harvest Gold White Bread", "400 g")
    res = client.post(
        "/api/instore/1/checkout",
        headers=headers,
        json={"items": [{"product_id": bread.id, "quantity": 1}], "payment_method": "online"},
    )
    assert res.status_code == 201, res.text
    return res.json()


def _session(client, headers, order_id: int) -> dict:
    res = client.post(f"/api/payments/orders/{order_id}/session", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def _verify(client, headers, order_id: int, rp_order_id: str, payment_id: str, signature: str | None = None):
    return client.post(
        f"/api/payments/orders/{order_id}/razorpay/verify",
        headers=headers,
        json={
            "razorpay_order_id": rp_order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature or _checkout_signature(rp_order_id, payment_id),
        },
    )


def _webhook(client, fake: FakeRazorpay, event: str, payment_id: str, secret: str = WEBHOOK_SECRET):
    payment = fake.payments[payment_id]
    payload = {"payment": {"entity": payment}}
    if event == "order.paid":
        payload["order"] = {"entity": {**fake.orders[payment["order_id"]], "status": "paid"}}
    raw = json.dumps({"entity": "event", "event": event, "contains": list(payload), "payload": payload})
    signature = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return client.post(
        "/api/payments/razorpay/webhook",
        content=raw,
        headers={"X-Razorpay-Signature": signature, "Content-Type": "application/json"},
    )


def _backdate(db, order_id: int, minutes: int = 16) -> None:
    db.execute(
        update(Order).where(Order.id == order_id).values(created_at=utcnow() - timedelta(minutes=minutes))
    )
    db.commit()


def _order(client, headers, order_id: int) -> dict:
    return client.get(f"/api/orders/{order_id}", headers=headers).json()


# --- Simulated payments (no Razorpay keys: development and demo deployments) -----------------------


def test_online_order_is_held_until_paid(client, db, customer):
    milk = find_product(db, "Amul Taaza Toned Milk", "500 ml")
    before = stock_of(db, 1, milk.id)
    order = _place(client, db, customer)
    assert order["status"] == "payment_pending" and order["payment_due"]
    assert order["status_label"] == "Waiting for payment"
    assert order["payment"] is None and order["can_cancel"]
    assert order["timeline"][0]["label"] == "Waiting for payment" and order["timeline"][0]["current"]
    expires_in = datetime.fromisoformat(order["payment_expires_at"]) - utcnow()
    assert timedelta(minutes=14) < expires_in <= timedelta(minutes=15)
    assert stock_of(db, 1, milk.id) == before - 2  # held while the customer pays

    session = _session(client, customer, order["id"])
    assert session["provider"] == "simulated" and session["key_id"] is None
    assert session["amount"] == int(order["grand_total"] * 100) and session["currency"] == "INR"
    assert session["prefill"]["contact"] == "+919876543210"
    assert session["order_code"] == order["code"]

    declined = pay(client, customer, order["id"], outcome="failure")
    assert declined["status"] == "payment_pending" and declined["payment_due"]
    assert declined["payment"]["status"] == "failed"
    assert declined["payment"]["error"] == "Payment declined (simulated)"
    assert _session(client, customer, order["id"])["provider_order_id"] == session["provider_order_id"]

    paid = pay(client, customer, order["id"])
    assert paid["status"] == "placed" and paid["payment_status"] == "paid" and not paid["payment_due"]
    assert paid["payment_expires_at"] is None
    assert paid["payment"]["status"] == "paid" and paid["payment"]["method"] == "simulated"
    assert paid["timeline"][0]["status"] == "placed" and paid["timeline"][0]["done"]
    assert stock_of(db, 1, milk.id) == before - 2

    again = client.post(f"/api/payments/orders/{order['id']}/session", headers=customer)
    assert again.status_code == 409


def test_online_payment_needs_a_provider(client, db, customer, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "simulated_payments", False)
    assert client.get("/api/config").json()["payments"] == {
        "online": False,
        "provider": None,
        "key_id": None,
        "test_mode": False,
    }
    res = client.post(
        "/api/orders",
        headers=customer,
        json={
            "store_id": 1,
            "fulfillment_type": "delivery",
            "address_id": home_address_id(db),
            "payment_method": "online",
            "items": [{"product_id": find_product(db, "Amul Taaza Toned Milk", "500 ml").id, "quantity": 1}],
        },
    )
    assert res.status_code == 422
    assert "isn't available" in res.json()["detail"]

    # The simulator is never offered in production, whatever the setting says.
    monkeypatch.setattr(settings, "simulated_payments", True)
    monkeypatch.setattr(settings, "environment", "production")
    assert settings.payment_provider is None


def test_unpaid_orders_expire_and_release_stock(client, db, customer):
    milk = find_product(db, "Amul Taaza Toned Milk", "500 ml")
    before = stock_of(db, 1, milk.id)
    order = _place(client, db, customer, kind="pickup")
    _session(client, customer, order["id"])
    _backdate(db, order["id"])

    expired = _order(client, customer, order["id"])
    assert expired["status"] == "cancelled" and not expired["payment_due"]
    assert [step["status"] for step in expired["timeline"]] == ["payment_pending", "cancelled"]
    assert expired["payment"]["status"] == "failed"
    assert expired["payment"]["error"] == "Expired before payment"
    assert stock_of(db, 1, milk.id) == before
    late = client.post(f"/api/payments/orders/{order['id']}/session", headers=customer)
    assert late.status_code == 409


def test_expiry_job_only_touches_overdue_orders(client, db, customer):
    old = _place(client, db, customer)
    fresh = _place(client, db, customer)
    _backdate(db, old["id"])

    assert expire_unpaid_orders(db) == 1
    db.expire_all()
    assert db.get(Order, old["id"]).status == "cancelled"
    assert db.get(Order, fresh["id"]).status == "payment_pending"
    assert expire_unpaid_orders(db) == 0


def test_cancelling_a_paid_order_refunds_it(client, db, customer):
    milk = find_product(db, "Amul Taaza Toned Milk", "500 ml")
    before = stock_of(db, 1, milk.id)
    order = _place(client, db, customer)
    pay(client, customer, order["id"])

    cancelled = client.post(f"/api/orders/{order['id']}/cancel", headers=customer).json()
    assert cancelled["status"] == "cancelled" and cancelled["payment_status"] == "refunded"
    assert cancelled["payment"]["status"] == "refunded"
    assert cancelled["payment"]["refund_id"].startswith("sim_rfnd_")
    assert stock_of(db, 1, milk.id) == before


def test_simulator_is_off_once_razorpay_is_configured(client, db, customer, razorpay):
    order = _place(client, db, customer)
    _session(client, customer, order["id"])
    res = client.post(f"/api/payments/orders/{order['id']}/simulate", headers=customer, json={})
    assert res.status_code == 404


# --- Razorpay ----------------------------------------------------------------------------------------


def test_razorpay_checkout_flow(client, db, customer, razorpay):
    config = client.get("/api/config").json()["payments"]
    assert config == {"online": True, "provider": "razorpay", "key_id": KEY_ID, "test_mode": True}

    order = _place(client, db, customer)
    session = _session(client, customer, order["id"])
    rp_order_id = session["provider_order_id"]
    assert session["provider"] == "razorpay" and session["key_id"] == KEY_ID
    created = razorpay.orders[rp_order_id]
    assert created["amount"] == session["amount"] == int(order["grand_total"] * 100)
    assert created["currency"] == "INR" and created["receipt"] == order["code"]
    assert created["notes"] == {"order_code": order["code"], "order_id": str(order["id"])}
    auth = razorpay.requests[0].headers["authorization"]
    assert auth == "Basic " + base64.b64encode(f"{KEY_ID}:{KEY_SECRET}".encode()).decode()

    # Retrying (closed the popup, card declined...) reuses the same Razorpay order.
    assert _session(client, customer, order["id"])["provider_order_id"] == rp_order_id
    assert len(razorpay.calls("POST", "/v1/orders")) == 1

    payment_id = razorpay.pay(rp_order_id)
    forged = _verify(client, customer, order["id"], rp_order_id, payment_id, signature="0" * 64)
    assert forged.status_code == 400
    assert _order(client, customer, order["id"])["status"] == "payment_pending"

    verified = _verify(client, customer, order["id"], rp_order_id, payment_id)
    assert verified.status_code == 200, verified.text
    paid = verified.json()
    assert paid["status"] == "placed" and paid["payment_status"] == "paid"
    assert paid["payment"] == {
        "provider": "razorpay",
        "status": "paid",
        "method": "upi",
        "reference": payment_id,
        "refund_id": None,
        "error": None,
    }

    # Razorpay's webhook for the same payment arrives afterwards: recorded once.
    assert _webhook(client, razorpay, "payment.captured", payment_id).json() == {"status": "ok"}
    assert _verify(client, customer, order["id"], rp_order_id, payment_id).status_code == 200
    db.expire_all()
    assert [e.status for e in db.get(Order, order["id"]).events] == ["payment_pending", "placed"]


def test_razorpay_payment_must_belong_to_the_order(client, db, customer, razorpay):
    first = _place(client, db, customer, quantity=3)
    second = _place(client, db, customer, quantity=1)
    first_rp = _session(client, customer, first["id"])["provider_order_id"]
    second_rp = _session(client, customer, second["id"])["provider_order_id"]

    # A genuine (cheaper) payment for the second order can't settle the first one.
    cheap = razorpay.pay(second_rp)
    reused = _verify(client, customer, first["id"], second_rp, cheap)
    assert reused.status_code == 400

    # Nor can a payment of the wrong amount, even against the right Razorpay order.
    short = razorpay.pay(first_rp, amount=100)
    assert _verify(client, customer, first["id"], first_rp, short).status_code == 400
    assert _order(client, customer, first["id"])["payment_status"] == "pending"


def test_razorpay_authorized_payment_is_captured(client, db, customer, razorpay):
    order = _place(client, db, customer)
    rp_order_id = _session(client, customer, order["id"])["provider_order_id"]
    payment_id = razorpay.pay(rp_order_id, status="authorized")

    assert _verify(client, customer, order["id"], rp_order_id, payment_id).json()["status"] == "placed"
    capture = razorpay.calls("POST", f"/v1/payments/{payment_id}/capture")
    assert (
        len(capture) == 1
        and json.loads(capture[0].content)["amount"] == razorpay.orders[rp_order_id]["amount"]
    )


def test_razorpay_outage_during_confirmation_is_reconciled(client, db, customer, razorpay):
    order = _place(client, db, customer)
    rp_order_id = _session(client, customer, order["id"])["provider_order_id"]
    payment_id = razorpay.pay(rp_order_id)

    razorpay.failing["GET /payments"] = 503
    pending = _verify(client, customer, order["id"], rp_order_id, payment_id)
    assert pending.status_code == 502 and "confirming" in pending.json()["detail"]
    assert _order(client, customer, order["id"])["status"] == "payment_pending"

    razorpay.failing.clear()
    refreshed = client.post(f"/api/payments/orders/{order['id']}/refresh", headers=customer).json()
    assert refreshed["status"] == "placed" and refreshed["payment"]["reference"] == payment_id


def test_razorpay_gateway_down_when_starting_payment(client, db, customer, razorpay):
    order = _place(client, db, customer)
    razorpay.failing["POST /orders"] = 500
    res = client.post(f"/api/payments/orders/{order['id']}/session", headers=customer)
    assert res.status_code == 502
    assert _order(client, customer, order["id"])["payment"] is None

    razorpay.failing.clear()
    assert _session(client, customer, order["id"])["provider"] == "razorpay"


def test_razorpay_webhooks(client, db, customer, razorpay):
    order = _place(client, db, customer)
    rp_order_id = _session(client, customer, order["id"])["provider_order_id"]
    declined = razorpay.pay(rp_order_id, status="failed", error_description="Your bank declined this payment")
    payment_id = razorpay.pay(rp_order_id)

    bad = _webhook(client, razorpay, "order.paid", payment_id, secret="not-the-secret")
    assert bad.status_code == 400
    assert _order(client, customer, order["id"])["status"] == "payment_pending"

    assert _webhook(client, razorpay, "payment.failed", declined).status_code == 200
    failed = _order(client, customer, order["id"])
    assert failed["payment"]["status"] == "failed"
    assert failed["payment"]["error"] == "Your bank declined this payment"

    razorpay.payments[payment_id]["amount"] -= 1  # tampered or partial: never accepted
    assert _webhook(client, razorpay, "order.paid", payment_id).status_code == 200
    assert _order(client, customer, order["id"])["status"] == "payment_pending"

    razorpay.payments[payment_id]["amount"] += 1
    assert _webhook(client, razorpay, "order.paid", payment_id).status_code == 200
    assert _webhook(client, razorpay, "order.paid", payment_id).status_code == 200  # Razorpay retries
    paid = _order(client, customer, order["id"])
    assert paid["status"] == "placed" and paid["payment"]["reference"] == payment_id
    db.expire_all()
    assert [e.status for e in db.get(Order, order["id"]).events] == ["payment_pending", "placed"]

    # Events for payments that aren't ours are acknowledged and ignored.
    stranger = f"order_{secrets.token_hex(7)}"
    razorpay.orders[stranger] = {"id": stranger, "amount": 100}
    assert _webhook(client, razorpay, "payment.captured", razorpay.pay(stranger)).status_code == 200


def test_razorpay_webhook_is_off_without_a_secret(client, db, customer, razorpay, monkeypatch):
    order = _place(client, db, customer)
    rp_order_id = _session(client, customer, order["id"])["provider_order_id"]
    payment_id = razorpay.pay(rp_order_id)
    monkeypatch.setattr(get_settings(), "razorpay_webhook_secret", None)
    assert _webhook(client, razorpay, "payment.captured", payment_id).status_code == 404


def test_expiry_asks_razorpay_before_cancelling(client, db, customer, razorpay):
    order = _place(client, db, customer)
    rp_order_id = _session(client, customer, order["id"])["provider_order_id"]
    payment_id = razorpay.pay(rp_order_id)  # paid, but the tab was closed and no webhook came
    _backdate(db, order["id"])

    assert expire_unpaid_orders(db) == 0
    assert _order(client, customer, order["id"])["payment"]["reference"] == payment_id
    assert _order(client, customer, order["id"])["status"] == "placed"


def test_late_payment_for_an_expired_order_is_refunded(client, db, customer, razorpay):
    order = _place(client, db, customer)
    rp_order_id = _session(client, customer, order["id"])["provider_order_id"]
    _backdate(db, order["id"])
    assert _order(client, customer, order["id"])["status"] == "cancelled"

    payment_id = razorpay.pay(rp_order_id)  # the customer finally pays
    assert _webhook(client, razorpay, "payment.captured", payment_id).status_code == 200
    late = _order(client, customer, order["id"])
    assert late["status"] == "cancelled" and late["payment_status"] == "refunded"
    assert late["payment"]["status"] == "refunded"
    assert razorpay.refunds == [
        {
            "id": late["payment"]["refund_id"],
            "payment_id": payment_id,
            "amount": razorpay.orders[rp_order_id]["amount"],
            "notes": {
                "order_code": order["code"],
                "reason": "Order was cancelled before the payment arrived",
            },
        }
    ]


def test_cancel_refunds_through_razorpay_or_not_at_all(client, db, customer, staff, razorpay):
    milk = find_product(db, "Amul Taaza Toned Milk", "500 ml")
    before = stock_of(db, 1, milk.id)
    order = _place(client, db, customer, kind="pickup")
    rp_order_id = _session(client, customer, order["id"])["provider_order_id"]
    payment_id = razorpay.pay(rp_order_id)
    assert _verify(client, customer, order["id"], rp_order_id, payment_id).json()["status"] == "placed"

    razorpay.failing[f"POST /payments/{payment_id}/refund"] = 500
    failed = client.post(
        f"/api/staff/orders/{order['id']}/status", headers=staff, json={"status": "cancelled"}
    )
    assert failed.status_code == 502
    kept = _order(client, customer, order["id"])
    assert kept["status"] == "placed" and kept["payment_status"] == "paid"
    assert stock_of(db, 1, milk.id) == before - 2  # nothing released either

    razorpay.failing.clear()
    cancelled = client.post(f"/api/orders/{order['id']}/cancel", headers=customer).json()
    assert cancelled["status"] == "cancelled" and cancelled["payment_status"] == "refunded"
    assert [r["payment_id"] for r in razorpay.refunds] == [payment_id]
    assert stock_of(db, 1, milk.id) == before


def test_instore_counter_checks_for_an_app_payment_first(client, db, customer, staff, razorpay):
    bill = _instore_bill(client, db, customer)
    rp_order_id = _session(client, customer, bill["id"])["provider_order_id"]
    razorpay.pay(rp_order_id)  # paid on the phone a moment before reaching the counter

    closed = client.post(f"/api/staff/orders/{bill['id']}/complete", headers=staff, json={})
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "completed" and closed.json()["payment_method"] == "online"
    assert razorpay.refunds == []


def test_instore_app_payment_after_paying_at_counter_is_refunded(client, db, customer, staff, razorpay):
    bill = _instore_bill(client, db, customer)
    rp_order_id = _session(client, customer, bill["id"])["provider_order_id"]
    closed = client.post(f"/api/staff/orders/{bill['id']}/complete", headers=staff, json={}).json()
    assert closed["status"] == "completed" and closed["payment_method"] == "pay_at_store"

    payment_id = razorpay.pay(rp_order_id)  # the app payment went through after all
    assert _webhook(client, razorpay, "payment.captured", payment_id).status_code == 200
    after = _order(client, customer, bill["id"])
    assert after["payment_status"] == "paid" and after["payment"]["status"] == "refunded"
    assert [r["payment_id"] for r in razorpay.refunds] == [payment_id]


def test_cancelling_an_unpaid_order_checks_for_a_payment_first(client, db, customer, razorpay):
    order = _place(client, db, customer)
    rp_order_id = _session(client, customer, order["id"])["provider_order_id"]
    payment_id = razorpay.pay(rp_order_id)  # paid; the confirmation is still on its way
    cancelled = client.post(f"/api/orders/{order['id']}/cancel", headers=customer).json()
    assert cancelled["status"] == "cancelled" and cancelled["payment_status"] == "refunded"
    assert [r["payment_id"] for r in razorpay.refunds] == [payment_id]

    # A bill paid in the app means the shopper has the goods: it can't be cancelled any more.
    bill = _instore_bill(client, db, customer)
    razorpay.pay(_session(client, customer, bill["id"])["provider_order_id"])
    assert client.post(f"/api/orders/{bill['id']}/cancel", headers=customer).status_code == 409
    assert _order(client, customer, bill["id"])["status"] == "completed"
