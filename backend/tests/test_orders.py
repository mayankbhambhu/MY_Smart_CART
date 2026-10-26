from app.services.pricing import FREE_DELIVERY_THRESHOLD
from conftest import STORE_ID, in_stock_products, login


def _stock(client, product_id):
    return client.get(f"/api/products/{product_id}", params={"store_id": STORE_ID}).json()["stock"]


def _first_tomorrow_slot(client):
    days = client.get(f"/api/stores/{STORE_ID}/pickup-slots").json()["days"]
    return days[1]["slots"][0]


def test_quote_matches_placed_order(client, customer, address_id):
    products = in_stock_products(client)
    items = [{"product_id": p["id"], "quantity": 1} for p in products]
    quote = client.post("/api/cart/quote", json={"store_id": STORE_ID, "fulfillment": "delivery", "items": items})
    assert quote.status_code == 200 and quote.json()["can_checkout"]

    order = client.post(
        "/api/orders",
        json={"store_id": STORE_ID, "fulfillment": "delivery", "items": items, "address_id": address_id},
        headers=customer,
    ).json()
    assert order["bill"] == {**quote.json()["bill"], "free_delivery_threshold_paise": None, "amount_to_free_delivery_paise": None}
    assert order["status"] == "placed"
    assert order["eta_minutes"] >= 8
    assert order["delivery_address"].startswith("12, 5th Cross")


def test_delivery_order_lifecycle(client, customer, staff, address_id):
    product = in_stock_products(client, count=1)[0]
    before = _stock(client, product["id"])
    qty = 2
    order = client.post(
        "/api/orders",
        json={
            "store_id": STORE_ID,
            "fulfillment": "delivery",
            "items": [{"product_id": product["id"], "quantity": qty}],
            "address_id": address_id,
            "payment_method": "cash",
        },
        headers=customer,
    ).json()
    assert _stock(client, product["id"]) == before - qty
    assert order["payment_status"] == "pending"
    assert order["code"] is None

    statuses = []
    for _ in range(3):
        res = client.post(f"/api/staff/orders/{order['id']}/advance", headers=staff)
        statuses.append(res.json()["status"])
    assert statuses == ["packed", "out_for_delivery", "delivered"]

    final = client.get(f"/api/orders/{order['id']}", headers=customer).json()
    assert final["payment_status"] == "paid"  # cash collected on delivery
    assert all(step["done"] for step in final["steps"])
    assert client.post(f"/api/staff/orders/{order['id']}/advance", headers=staff).status_code == 400


def test_delivery_needs_an_address_in_range(client, customer):
    product = in_stock_products(client, count=1)[0]
    far = {"label": "Work", "line1": "Bandra West", "city": "Mumbai", "pincode": "400050", "lat": 19.06, "lng": 72.83}
    far_id = client.post("/api/addresses", json=far, headers=customer).json()["id"]
    base = {"store_id": STORE_ID, "fulfillment": "delivery", "items": [{"product_id": product["id"], "quantity": 1}]}
    assert client.post("/api/orders", json=base, headers=customer).status_code == 400
    res = client.post("/api/orders", json={**base, "address_id": far_id}, headers=customer)
    assert res.status_code == 400 and "deliver" in res.json()["detail"]


def test_pickup_order_with_slot_and_code(client, customer, staff):
    product = in_stock_products(client, count=1)[0]
    slot = _first_tomorrow_slot(client)
    order = client.post(
        "/api/orders",
        json={
            "store_id": STORE_ID,
            "fulfillment": "pickup",
            "items": [{"product_id": product["id"], "quantity": 1}],
            "pickup_slot_start": slot["start"],
            "payment_method": "upi",
        },
        headers=customer,
    ).json()
    assert order["status"] == "placed"
    assert order["payment_status"] == "paid"
    assert order["bill"]["delivery_fee_paise"] == 0 and order["bill"]["handling_fee_paise"] > 0
    assert len(order["code"]) == 4
    assert order["items"][0]["location"]["label"].startswith("Aisle ")

    # The slot's remaining capacity goes down.
    assert _first_tomorrow_slot(client)["remaining"] == slot["remaining"] - 1

    found = client.post("/api/staff/verify-code", json={"store_id": STORE_ID, "code": order["code"]}, headers=staff)
    assert found.json()["id"] == order["id"]
    assert found.json()["next_status"] == "packed"
    for expected in ["packed", "ready_for_pickup", "picked_up"]:
        assert client.post(f"/api/staff/orders/{order['id']}/advance", headers=staff).json()["status"] == expected


def test_pickup_rejects_unknown_slot(client, customer):
    product = in_stock_products(client, count=1)[0]
    res = client.post(
        "/api/orders",
        json={
            "store_id": STORE_ID,
            "fulfillment": "pickup",
            "items": [{"product_id": product["id"], "quantity": 1}],
            "pickup_slot_start": "2020-01-01T10:00:00+05:30",
        },
        headers=customer,
    )
    assert res.status_code == 400


def test_in_store_cash_checkout(client, customer, staff):
    products = in_stock_products(client, count=2)
    items = [{"product_id": p["id"], "quantity": 1} for p in products]
    order = client.post(
        "/api/orders",
        json={"store_id": STORE_ID, "fulfillment": "in_store", "items": items, "payment_method": "cash"},
        headers=customer,
    ).json()
    assert order["status"] == "awaiting_payment"
    assert order["bill"]["total_paise"] == sum(p["price_paise"] for p in products)
    assert len(order["code"]) == 6

    found = client.post(
        "/api/staff/verify-code", json={"store_id": STORE_ID, "code": order["code"].lower()}, headers=staff
    ).json()
    assert found["id"] == order["id"]
    done = client.post(f"/api/staff/orders/{order['id']}/advance", headers=staff).json()
    assert done["status"] == "completed" and done["payment_status"] == "paid"


def test_in_store_online_payment_completes_immediately(client, customer):
    product = in_stock_products(client, count=1)[0]
    order = client.post(
        "/api/orders",
        json={
            "store_id": STORE_ID,
            "fulfillment": "in_store",
            "items": [{"product_id": product["id"], "quantity": 1}],
            "payment_method": "upi",
        },
        headers=customer,
    ).json()
    assert order["status"] == "completed"
    assert order["payment_status"] == "paid"


def test_cancel_restocks(client, customer, address_id):
    product = in_stock_products(client, count=1)[0]
    before = _stock(client, product["id"])
    order = client.post(
        "/api/orders",
        json={
            "store_id": STORE_ID,
            "fulfillment": "delivery",
            "items": [{"product_id": product["id"], "quantity": 3}],
            "address_id": address_id,
            "payment_method": "card",
        },
        headers=customer,
    ).json()
    cancelled = client.post(f"/api/orders/{order['id']}/cancel", headers=customer).json()
    assert cancelled["status"] == "cancelled"
    assert cancelled["payment_status"] == "refunded"
    assert cancelled["steps"][-1]["status"] == "cancelled"
    assert _stock(client, product["id"]) == before
    assert client.post(f"/api/orders/{order['id']}/cancel", headers=customer).status_code == 400


def test_cannot_oversell(client, customer, address_id):
    product = in_stock_products(client, count=1)[0]
    res = client.post(
        "/api/orders",
        json={
            "store_id": STORE_ID,
            "fulfillment": "delivery",
            "items": [{"product_id": product["id"], "quantity": product["stock"] + 1}],
            "address_id": address_id,
        },
        headers=customer,
    )
    assert res.status_code == 409


def test_free_delivery_above_threshold(client, customer, address_id):
    product = max(in_stock_products(client, count=50), key=lambda p: p["price_paise"])
    qty = -(-FREE_DELIVERY_THRESHOLD // product["price_paise"])  # ceil
    qty = min(qty, product["stock"])
    quote = client.post(
        "/api/cart/quote",
        json={"store_id": STORE_ID, "items": [{"product_id": product["id"], "quantity": qty}]},
    ).json()
    if quote["bill"]["item_total_paise"] >= FREE_DELIVERY_THRESHOLD:
        assert quote["bill"]["delivery_fee_paise"] == 0


def test_orders_are_private(client, customer, address_id):
    product = in_stock_products(client, count=1)[0]
    order = client.post(
        "/api/orders",
        json={
            "store_id": STORE_ID,
            "fulfillment": "delivery",
            "items": [{"product_id": product["id"], "quantity": 1}],
            "address_id": address_id,
        },
        headers=customer,
    ).json()
    other = login(client, "9123456780")
    assert client.get(f"/api/orders/{order['id']}", headers=other).status_code == 404
    assert client.get("/api/orders", headers=other).json() == []
    assert len(client.get("/api/orders", headers=customer).json()) == 1


def test_staff_endpoints_need_staff_role(client, customer):
    assert client.get("/api/staff/orders", params={"store_id": STORE_ID}, headers=customer).status_code == 403


def test_staff_sees_active_orders(client, customer, staff, address_id):
    product = in_stock_products(client, count=1)[0]
    client.post(
        "/api/orders",
        json={
            "store_id": STORE_ID,
            "fulfillment": "delivery",
            "items": [{"product_id": product["id"], "quantity": 1}],
            "address_id": address_id,
        },
        headers=customer,
    )
    orders = client.get("/api/staff/orders", params={"store_id": STORE_ID}, headers=staff).json()
    assert len(orders) == 1
    assert orders[0]["customer_phone"] == "9876543210"
    assert orders[0]["next_status_label"] == "Packed"
