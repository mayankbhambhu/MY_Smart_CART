from datetime import timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.models import Address, Order, Product, StoreInventory, User
from app.services.orders import simulate_progress
from tests.conftest import DEMO_CUSTOMER, STAFF_DLF, login


def _product(db, name: str, unit: str) -> Product:
    return db.scalars(select(Product).where(Product.name == name, Product.unit_label == unit)).one()


def _stock(db, store_id: int, product_id: int) -> int:
    db.expire_all()
    return db.scalar(
        select(StoreInventory.stock).where(
            StoreInventory.store_id == store_id, StoreInventory.product_id == product_id
        )
    )


def _address_id(db) -> int:
    user = db.scalars(select(User).where(User.phone == DEMO_CUSTOMER)).one()
    return db.scalars(select(Address.id).where(Address.user_id == user.id)).first()


def _first_slot(client, store_id: int = 1) -> str:
    days = client.get(f"/api/stores/{store_id}/pickup-slots").json()
    return next(slot["start"] for day in days for slot in day["slots"] if slot["available"])


def test_delivery_order_reserves_stock_and_can_be_cancelled(client, db, customer):
    atta = _product(db, "Aashirvaad Shudh Chakki Atta", "5 kg")
    before = _stock(db, 1, atta.id)

    res = client.post(
        "/api/orders",
        headers=customer,
        json={
            "store_id": 1,
            "fulfillment_type": "delivery",
            "address_id": _address_id(db),
            "payment_method": "cod",
            "items": [{"product_id": atta.id, "quantity": 2}],
        },
    )
    assert res.status_code == 201, res.text
    order = res.json()
    assert order["code"].startswith("SC")
    assert order["status"] == "placed"
    assert order["grand_total"] == 510 + 2  # free delivery above ₹199, ₹2 handling
    assert order["eta_minutes"] >= 8
    assert order["timeline"][0]["done"] and not order["timeline"][1]["done"]
    assert order["items"][0]["location"]["label"].startswith("Aisle 3")
    assert _stock(db, 1, atta.id) == before - 2

    listed = client.get("/api/orders", headers=customer).json()
    assert listed[0]["code"] == order["code"]

    cancelled = client.post(f"/api/orders/{order['id']}/cancel", headers=customer).json()
    assert cancelled["status"] == "cancelled"
    assert _stock(db, 1, atta.id) == before


def test_delivery_validation(client, db, customer):
    milk = _product(db, "Amul Taaza Toned Milk", "500 ml")
    base = {"store_id": 1, "fulfillment_type": "delivery", "items": [{"product_id": milk.id, "quantity": 1}]}

    no_address = client.post("/api/orders", headers=customer, json={**base, "payment_method": "cod"})
    assert no_address.status_code == 422
    assert no_address.json()["detail"] == "Please choose a delivery address"

    wrong_payment = client.post(
        "/api/orders",
        headers=customer,
        json={**base, "payment_method": "pay_at_store", "address_id": _address_id(db)},
    )
    assert wrong_payment.status_code == 422

    too_far = client.post(  # the Sohna Road store is ~6 km away, beyond its 5 km radius
        "/api/orders",
        headers=customer,
        json={**base, "store_id": 3, "payment_method": "cod", "address_id": _address_id(db)},
    )
    assert too_far.status_code == 422


def test_cannot_order_more_than_in_stock(client, db, customer):
    milk = _product(db, "Amul Taaza Toned Milk", "500 ml")
    stock = _stock(db, 1, milk.id)
    res = client.post(
        "/api/orders",
        headers=customer,
        json={
            "store_id": 1,
            "fulfillment_type": "delivery",
            "address_id": _address_id(db),
            "payment_method": "cod",
            "items": [{"product_id": milk.id, "quantity": stock + 1}],
        },
    )
    assert res.status_code == 409
    assert res.json()["details"]["issues"]
    assert _stock(db, 1, milk.id) == stock


def test_scheduled_pickup_flow_with_pin_handover(client, db, customer, staff):
    bread = _product(db, "Harvest Gold White Bread", "400 g")
    slot = _first_slot(client)
    res = client.post(
        "/api/orders",
        headers=customer,
        json={
            "store_id": 1,
            "fulfillment_type": "pickup",
            "pickup_slot_start": slot,
            "payment_method": "pay_at_store",
            "items": [{"product_id": bread.id, "quantity": 1}],
        },
    )
    assert res.status_code == 201, res.text
    order = res.json()
    assert order["delivery_fee"] == 0 and order["small_cart_fee"] == 0
    assert order["grand_total"] == 43 + 2
    assert len(order["handover_pin"]) == 4
    assert order["pickup_slot_start"]

    # The store team sees the order (but not the customer's PIN) and works through it.
    queue = client.get("/api/staff/orders", headers=staff, params={"fulfillment_type": "pickup"}).json()
    assert [o["code"] for o in queue] == [order["code"]]
    assert queue[0]["handover_pin"] is None and queue[0]["customer"]["phone"] == DEMO_CUSTOMER

    oid = order["id"]
    too_early = client.post(
        f"/api/staff/orders/{oid}/complete", headers=staff, json={"pin": order["handover_pin"]}
    )
    assert too_early.status_code == 409
    for status in ["confirmed", "packing", "ready_for_pickup"]:
        step = client.post(f"/api/staff/orders/{oid}/status", headers=staff, json={"status": status})
        assert step.status_code == 200, step.text

    wrong = "0000" if order["handover_pin"] != "0000" else "1111"
    assert (
        client.post(f"/api/staff/orders/{oid}/complete", headers=staff, json={"pin": wrong}).status_code
        == 400
    )
    done = client.post(
        f"/api/staff/orders/{oid}/complete", headers=staff, json={"pin": order["handover_pin"]}
    )
    assert done.json()["status"] == "picked_up"
    assert done.json()["payment_status"] == "paid"

    mine = client.get(f"/api/orders/{oid}", headers=customer).json()
    assert [s["done"] for s in mine["timeline"]] == [True] * 5
    assert client.post(f"/api/orders/{oid}/cancel", headers=customer).status_code == 409


def test_pickup_validation(client, db, customer):
    bread = _product(db, "Harvest Gold White Bread", "400 g")
    base = {"store_id": 1, "fulfillment_type": "pickup", "items": [{"product_id": bread.id, "quantity": 1}]}
    assert (
        client.post("/api/orders", headers=customer, json={**base, "payment_method": "online"}).status_code
        == 422
    )
    cod = client.post(
        "/api/orders",
        headers=customer,
        json={**base, "payment_method": "cod", "pickup_slot_start": _first_slot(client)},
    )
    assert cod.status_code == 422


def test_staff_access_is_scoped(client, db, customer, staff):
    assert client.get("/api/staff/orders", headers=customer).status_code == 403

    bread = _product(db, "Harvest Gold White Bread", "400 g")
    order = client.post(
        "/api/orders",
        headers=customer,
        json={
            "store_id": 1,
            "fulfillment_type": "pickup",
            "pickup_slot_start": _first_slot(client),
            "payment_method": "online",
            "items": [{"product_id": bread.id, "quantity": 1}],
        },
    ).json()
    assert order["payment_status"] == "paid"

    other_store = login(client, STAFF_DLF)
    assert client.get("/api/staff/orders", headers=other_store).json() == []
    lookup = client.get("/api/staff/orders/lookup", headers=other_store, params={"code": order["code"]})
    assert lookup.status_code == 404
    found = client.get("/api/staff/orders/lookup", headers=staff, params={"code": order["code"].lower()})
    assert found.json()["id"] == order["id"]


def test_demo_mode_moves_delivery_orders_along(client, db, customer, monkeypatch):
    milk = _product(db, "Amul Taaza Toned Milk", "500 ml")
    created = client.post(
        "/api/orders",
        headers=customer,
        json={
            "store_id": 1,
            "fulfillment_type": "delivery",
            "address_id": _address_id(db),
            "payment_method": "cod",
            "items": [{"product_id": milk.id, "quantity": 1}],
        },
    ).json()
    monkeypatch.setattr(get_settings(), "simulate_order_progress", True)
    order = db.get(Order, created["id"])

    assert simulate_progress(db, order, now=order.created_at + timedelta(seconds=90))
    assert order.status == "packing"
    assert simulate_progress(db, order, now=order.created_at + timedelta(hours=1))
    assert order.status == "delivered" and order.payment_status == "paid"
    assert [e.status for e in order.events] == [
        "placed",
        "confirmed",
        "packing",
        "out_for_delivery",
        "delivered",
    ]
