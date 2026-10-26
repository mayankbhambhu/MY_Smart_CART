from sqlalchemy import select

from app.models import Product, StoreInventory
from app.services.matching import parse_chunk, walking_route


def _resolve(client, text: str, store_id: int = 1) -> dict:
    res = client.post(f"/api/instore/{store_id}/resolve", json={"text": text})
    assert res.status_code == 200, res.text
    return res.json()


def _by_query(result: dict) -> dict[str, dict]:
    return {item["query"]: item for item in result["items"]}


def test_parse_quantities_and_sizes():
    def parsed(text):
        return [(" ".join(r.words), r.quantity, r.size) for r in parse_chunk(text)]

    assert parsed("2 milk 3 bread") == [("milk", 2, None), ("bread", 3, None)]
    assert parsed("milk x2") == [("milk", 2, None)]
    assert parsed("1kg sugar") == [("sugar", 1, ("g", 1000.0))]
    assert parsed("sugar 1 kg") == [("sugar", 1, ("g", 1000.0))]
    assert parsed("do doodh") == [("doodh", 2, None)]
    assert parsed("two packets of maggi") == [("maggi", 2, None)]
    assert parsed("2 x 5kg atta") == [("atta", 2, ("g", 5000.0))]


def test_walking_route_snakes_through_needed_aisles():
    spots = [(5, 2), (2, 6), (2, 1), (5, 5), (2, 3)]
    ordered = [spots[i] for i in walking_route(spots)]
    assert ordered == [(2, 1), (2, 3), (2, 6), (5, 5), (5, 2)]


def test_shopping_list_shows_location_route_and_total(client):
    result = _resolve(client, "2 milk, bread, 6 eggs, 1kg atta, maggi")
    items = _by_query(result)
    assert set(items) == {"milk", "bread", "eggs", "atta", "maggi"}
    assert items["milk"]["quantity"] == 2
    assert items["eggs"]["quantity"] == 1  # six eggs is one 6-piece pack
    assert items["eggs"]["product"]["unit_label"] == "6 pcs"

    for item in result["items"]:
        location = item["product"]["location"]
        assert location["label"] == f"Aisle {location['aisle']} · Row {location['row']}"
    assert [i["step"] for i in result["items"]] == list(range(1, 6))
    aisles = [i["product"]["location"]["aisle"] for i in result["items"]]
    assert aisles == sorted(aisles)
    assert [stop["aisle"] for stop in result["route"]] == sorted(set(aisles))

    expected_total = sum(i["product"]["price"] * i["quantity"] for i in result["items"] if i["in_stock"])
    assert result["total"] == expected_total
    assert result["item_count"] == 6


def test_spoken_list_without_punctuation_is_split_into_items(client):
    assert set(_by_query(_resolve(client, "milk bread eggs"))) == {"milk", "bread", "eggs"}
    whole = _resolve(client, "milk bread")["items"]
    assert len(whole) == 1 and whole[0]["product"]["name"] == "Britannia Milk Bread"


def test_hindi_and_hinglish_lists(client):
    items = _by_query(_resolve(client, "do doodh aur ek kilo cheeni, pyaz"))
    assert items["doodh"]["quantity"] == 2 and "Milk" in items["doodh"]["product"]["name"]
    assert items["cheeni"]["product"]["unit_label"] == "1 kg"
    assert items["pyaz"]["product"]["name"] == "Onion"


def test_unknown_items_come_back_unmatched(client):
    result = _resolve(client, "bread, flux capacitor")
    assert [u["query"] for u in result["unmatched"]] == ["flux capacitor"]
    assert len(result["items"]) == 1


def test_same_product_has_store_specific_locations(client):
    first = _resolve(client, "maggi", store_id=1)["items"][0]["product"]["location"]
    second = _resolve(client, "maggi", store_id=2)["items"][0]["product"]["location"]
    assert first["aisle"] != second["aisle"]


def test_out_of_stock_items_are_located_but_not_totalled(client, db):
    bread = db.scalars(select(Product).where(Product.name == "Harvest Gold White Bread")).one()
    inv = db.scalars(
        select(StoreInventory).where(StoreInventory.store_id == 1, StoreInventory.product_id == bread.id)
    ).one()
    inv.stock = 0
    db.commit()

    result = client.post(
        "/api/instore/1/resolve",
        json={"items": [{"query": "white bread", "product_id": bread.id}, {"query": "milk", "quantity": 2}]},
    ).json()
    items = _by_query(result)
    assert items["white bread"]["in_stock"] is False
    assert items["white bread"]["product"]["location"] is not None
    assert result["out_of_stock_count"] == 1
    assert result["total"] == items["milk"]["line_total"]


def test_counter_checkout_and_cashier_verification(client, db, customer, staff):
    result = _resolve(client, "2 milk, chips")
    items = [{"product_id": i["product"]["id"], "quantity": i["quantity"]} for i in result["items"]]
    milk_id = _by_query(result)["milk"]["product"]["id"]
    db.expire_all()
    stock_before = db.scalar(
        select(StoreInventory.stock).where(StoreInventory.store_id == 1, StoreInventory.product_id == milk_id)
    )

    bill = client.post(
        "/api/instore/1/checkout", headers=customer, json={"items": items, "payment_method": "pay_at_store"}
    )
    assert bill.status_code == 201, bill.text
    bill = bill.json()
    assert bill["status"] == "awaiting_payment"
    assert bill["grand_total"] == result["total"]  # no delivery or handling fees in store
    assert bill["items"][0]["location"] is not None

    at_counter = client.get("/api/staff/orders/lookup", headers=staff, params={"code": bill["code"]}).json()
    assert at_counter["status"] == "awaiting_payment"
    paid = client.post(f"/api/staff/orders/{bill['id']}/complete", headers=staff, json={}).json()
    assert paid["status"] == "completed" and paid["payment_status"] == "paid"

    db.expire_all()
    stock_after = db.scalar(
        select(StoreInventory.stock).where(StoreInventory.store_id == 1, StoreInventory.product_id == milk_id)
    )
    assert stock_after == stock_before - 2


def test_pay_in_app_closes_the_bill_immediately(client, customer):
    result = _resolve(client, "bread")
    item = result["items"][0]
    bill = client.post(
        "/api/instore/1/checkout",
        headers=customer,
        json={"items": [{"product_id": item["product"]["id"], "quantity": 1}], "payment_method": "online"},
    ).json()
    assert bill["status"] == "completed"
    assert bill["payment_status"] == "paid"


def test_resolve_requires_something_to_look_up(client):
    assert client.post("/api/instore/1/resolve", json={"text": "  "}).status_code == 422
