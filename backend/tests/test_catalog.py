from conftest import HOME, STORE_ID


def test_categories_and_home_feed(client):
    categories = client.get("/api/categories").json()
    assert len(categories) >= 10
    rails = client.get("/api/home", params={"store_id": STORE_ID, "per_category": 4}).json()
    assert rails and all(1 <= len(r["products"]) <= 4 for r in rails)


def test_products_carry_price_stock_and_location(client):
    products = client.get("/api/products", params={"store_id": STORE_ID, "q": "milk"}).json()
    assert products[0]["name"] == "Amul Taaza Toned Milk"
    milk = products[0]
    assert milk["price_paise"] <= milk["mrp_paise"]
    assert milk["location"]["label"].startswith("Aisle ")

    detail = client.get(f"/api/products/{milk['id']}", params={"store_id": STORE_ID}).json()
    assert detail["location"] == milk["location"]


def test_search_handles_typos_and_synonyms(client):
    def top(q):
        return client.get("/api/products", params={"store_id": STORE_ID, "q": q}).json()[0]["name"]

    assert top("dahi") == "Mother Dairy Classic Curd"
    assert top("tomatos") == "Tomato"
    assert top("aloo") == "Potato"
    assert "Bread" in top("bred")


def test_category_filter(client):
    category = client.get("/api/categories").json()[0]
    products = client.get("/api/products", params={"store_id": STORE_ID, "category_id": category["id"]}).json()
    assert products and all(p["category_id"] == category["id"] for p in products)


def test_nearest_store_and_serviceability(client):
    store = client.get("/api/stores/nearest", params=HOME).json()
    assert store["id"] == STORE_ID
    assert store["delivers_here"] and store["delivery_eta_minutes"] >= 8
    # Mumbai is well outside every Bengaluru store's delivery radius.
    assert client.get("/api/stores/nearest", params={"lat": 19.07, "lng": 72.87}).status_code == 404


def test_stores_sorted_by_distance(client):
    stores = client.get("/api/stores", params=HOME).json()
    distances = [s["distance_km"] for s in stores]
    assert distances == sorted(distances)


def test_store_layout_and_pickup_slots(client):
    layout = client.get(f"/api/stores/{STORE_ID}").json()
    assert [a["number"] for a in layout["aisles"]] == list(range(1, len(layout["aisles"]) + 1))

    days = client.get(f"/api/stores/{STORE_ID}/pickup-slots").json()["days"]
    assert [d["label"] for d in days] == ["Today", "Tomorrow"]
    assert days[1]["slots"], "a 24h store always has slots tomorrow"
    assert all(s["available"] for s in days[1]["slots"])
