from app.models import Fulfillment
from app.services.pricing import (
    DELIVERY_FEE,
    FREE_DELIVERY_THRESHOLD,
    HANDLING_FEE,
    SMALL_CART_FEE,
    SMALL_CART_THRESHOLD,
    compute_bill,
)


def test_small_delivery_order_pays_all_fees():
    bill = compute_bill(Fulfillment.DELIVERY, SMALL_CART_THRESHOLD - 100, SMALL_CART_THRESHOLD)
    assert bill.delivery_fee_paise == DELIVERY_FEE
    assert bill.small_cart_fee_paise == SMALL_CART_FEE
    assert bill.handling_fee_paise == HANDLING_FEE
    assert bill.total_paise == SMALL_CART_THRESHOLD - 100 + DELIVERY_FEE + SMALL_CART_FEE + HANDLING_FEE
    assert bill.savings_paise == 100


def test_large_delivery_order_gets_free_delivery():
    bill = compute_bill(Fulfillment.DELIVERY, FREE_DELIVERY_THRESHOLD, FREE_DELIVERY_THRESHOLD)
    assert bill.delivery_fee_paise == 0
    assert bill.small_cart_fee_paise == 0
    assert bill.amount_to_free_delivery_paise == 0


def test_pickup_only_pays_handling_and_in_store_pays_nothing():
    pickup = compute_bill(Fulfillment.PICKUP, 5000, 6000)
    assert (pickup.delivery_fee_paise, pickup.small_cart_fee_paise, pickup.handling_fee_paise) == (0, 0, HANDLING_FEE)
    in_store = compute_bill(Fulfillment.IN_STORE, 5000, 6000)
    assert in_store.total_paise == 5000


def test_empty_cart_is_free():
    assert compute_bill(Fulfillment.DELIVERY, 0, 0).total_paise == 0
