import pytest


def test_category_tree_and_home_feed(client):
    categories = client.get("/api/categories").json()
    assert categories[0]["slug"] == "fruits-vegetables"
    assert all(c["children"] for c in categories)

    home = client.get("/api/home", params={"store_id": 1}).json()
    assert home["sections"]
    first = home["sections"][0]["products"][0]
    assert first["availability"]["in_stock"] is True
    assert first["location"]["label"].startswith("Aisle ")


def test_category_page_filters_by_subcategory(client):
    page = client.get("/api/categories/dairy-bread-eggs", params={"sub": "milk", "store_id": 1}).json()
    assert page["active_subcategory"] == "milk"
    assert {s["slug"] for s in page["subcategories"]} >= {"milk", "eggs", "bread-pav"}
    assert page["products"] and all("Milk" in p["name"] for p in page["products"])

    via_sub_slug = client.get("/api/categories/milk").json()
    assert via_sub_slug["category"]["slug"] == "dairy-bread-eggs"
    assert via_sub_slug["active_subcategory"] == "milk"

    assert client.get("/api/categories/nope").status_code == 404


def test_product_detail_has_store_location_and_similar_items(client):
    milk = client.get("/api/search", params={"q": "amul taaza"}).json()["products"][0]
    detail = client.get(f"/api/products/{milk['id']}", params={"store_id": 1}).json()
    assert detail["parent_category"]["slug"] == "dairy-bread-eggs"
    assert detail["location"]["aisle_name"] == "Dairy, Bread & Eggs"
    assert detail["similar"]

    other_store = client.get(f"/api/products/{milk['id']}", params={"store_id": 2}).json()
    assert other_store["location"]["aisle"] != detail["location"]["aisle"]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("doodh", "Milk"),
        ("pyaz", "Onion"),
        ("tomatos", "Tomato"),
        ("cheeni", "Sugar"),
        ("dairy milk", "Cadbury Dairy Milk"),
        ("brown bread", "Whole Wheat Bread"),
        ("mag", "Maggi"),
        ("coke", "Coca-Cola"),
        ("toothpaste", "Toothpaste"),
    ],
)
def test_search_understands_synonyms_typos_and_prefixes(client, query, expected):
    products = client.get("/api/search", params={"q": query}).json()["products"]
    assert products, query
    assert expected in products[0]["name"]


def test_search_prefers_requested_pack_size(client):
    products = client.get("/api/search", params={"q": "10kg atta"}).json()["products"]
    assert products[0]["unit_label"] == "10 kg"


def test_search_with_no_results(client):
    assert client.get("/api/search", params={"q": "zzqqxx"}).json()["products"] == []
