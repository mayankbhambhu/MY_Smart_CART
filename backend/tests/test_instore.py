from app.services.search import parse_shopping_list
from conftest import STORE_ID, in_stock_products


def parsed(text):
    return [(i.query, i.quantity) for i in parse_shopping_list(text)]


def test_parse_typed_list():
    assert parsed("2 milk, brown bread\n3x coke; eggs") == [
        ("milk", 2),
        ("brown bread", 1),
        ("coke", 3),
        ("eggs", 1),
    ]


def test_parse_spoken_list():
    assert parsed("I want two packets of chips and a bread and also some tomatoes") == [
        ("chips", 2),
        ("bread", 1),
        ("tomatoes", 1),
    ]


def test_parse_keeps_pack_sizes_and_trailing_quantities():
    assert parsed("1kg onion, milk x 4, 500 ml milk") == [("1 kg onion", 1), ("milk", 4), ("500 ml milk", 1)]


def test_match_returns_locations_and_unmatched(client):
    res = client.post(f"/api/stores/{STORE_ID}/instore/match", json={"text": "2 milk, dahi and qwertyuiop"})
    body = res.json()
    assert [m["query"] for m in body["matches"]] == ["milk", "dahi"]
    milk = body["matches"][0]
    assert milk["quantity"] == 2
    assert "Milk" in milk["product"]["name"]
    assert milk["product"]["location"]["label"].startswith("Aisle ")
    assert body["unmatched"] == ["qwertyuiop"]


def test_locations_differ_per_store(client):
    def aisle(store_id):
        res = client.post(f"/api/stores/{store_id}/instore/match", json={"text": "chips"})
        return res.json()["matches"][0]["product"]["location"]["aisle_number"]

    assert aisle(1) != aisle(2)


def test_shopping_route_is_sorted_and_totalled(client):
    products = client.get("/api/products", params={"store_id": STORE_ID, "limit": 200}).json()
    picks = [p for p in products if p["in_stock"]][::7][:6]
    items = [{"product_id": p["id"], "quantity": 2} for p in picks]
    body = client.post(f"/api/stores/{STORE_ID}/instore/list", json={"items": items}).json()

    keys = [(l["product"]["location"]["aisle_number"], l["product"]["location"]["row_number"]) for l in body["lines"]]
    assert keys == sorted(keys)
    assert body["bill"]["total_paise"] == sum(p["price_paise"] * 2 for p in picks)
    assert body["bill"]["delivery_fee_paise"] == 0 and body["bill"]["handling_fee_paise"] == 0
    assert body["store"]["aisles"]
    assert body["issues"] == []


def test_shopping_route_flags_stock_problems(client):
    product = in_stock_products(client, count=1)[0]
    items = [{"product_id": product["id"], "quantity": product["stock"] + 1}]
    body = client.post(f"/api/stores/{STORE_ID}/instore/list", json={"items": items}).json()
    assert body["issues"] and "left in stock" in body["issues"][0]
