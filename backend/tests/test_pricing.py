from decimal import Decimal

import pytest
from sqlalchemy import select, update

from app.models import FulfillmentType, Product, StoreInventory
from app.services.pricing import compute_bill


@pytest.mark.parametrize(
    ("fulfillment", "item_total", "delivery", "small_cart", "handling", "grand"),
    [
        (FulfillmentType.DELIVERY, 50, 25, 20, 2, 97),
        (FulfillmentType.DELIVERY, 150, 25, 0, 2, 177),
        (FulfillmentType.DELIVERY, 199, 0, 0, 2, 201),
        (FulfillmentType.PICKUP, 50, 0, 0, 2, 52),
        (FulfillmentType.IN_STORE, 50, 0, 0, 0, 50),
    ],
)
def test_bill_rules(fulfillment, item_total, delivery, small_cart, handling, grand):
    bill = compute_bill(Decimal(item_total), Decimal(item_total + 10), fulfillment)
    assert bill.delivery_fee == delivery
    assert bill.small_cart_fee == small_cart
    assert bill.handling_fee == handling
    assert bill.grand_total == grand
    assert bill.savings == 10


def _product_id(db, name: str, unit: str) -> int:
    return db.scalar(select(Product.id).where(Product.name == name, Product.unit_label == unit))


def test_quote_prices_cart_and_nudges_towards_free_delivery(client, db):
    milk = _product_id(db, "Amul Taaza Toned Milk", "500 ml")
    quote = client.post(
        "/api/cart/quote",
        json={"store_id": 1, "fulfillment_type": "delivery", "items": [{"product_id": milk, "quantity": 2}]},
    ).json()
    assert quote["bill"]["item_total"] == 56
    assert quote["bill"]["grand_total"] == 56 + 25 + 20 + 2
    assert quote["free_delivery_gap"] == 143
    assert quote["can_checkout"] is True
    assert any("FREE delivery" in note for note in quote["notes"])

    pickup = client.post(
        "/api/cart/quote",
        json={"store_id": 1, "fulfillment_type": "pickup", "items": [{"product_id": milk, "quantity": 2}]},
    ).json()
    assert pickup["bill"]["grand_total"] == 58
    assert any("saves you ₹45" in note for note in pickup["notes"])


def test_quote_flags_stock_problems(client, db):
    milk = _product_id(db, "Amul Taaza Toned Milk", "500 ml")
    db.execute(
        update(StoreInventory)
        .where(StoreInventory.store_id == 1, StoreInventory.product_id == milk)
        .values(stock=3)
    )
    db.commit()
    quote = client.post(
        "/api/cart/quote",
        json={
            "store_id": 1,
            "items": [{"product_id": milk, "quantity": 5}, {"product_id": 99999, "quantity": 1}],
        },
    ).json()
    line = quote["lines"][0]
    assert line["quantity"] == 3 and line["issue"] == "Only 3 left"
    assert quote["unavailable_product_ids"] == [99999]
    assert quote["can_checkout"] is False
