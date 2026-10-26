from ..models import Fulfillment
from ..schemas import Bill

# Fees are in paise. Tune these to match your business rules.
FREE_DELIVERY_THRESHOLD = 199_00
DELIVERY_FEE = 25_00
HANDLING_FEE = 2_00
SMALL_CART_THRESHOLD = 99_00
SMALL_CART_FEE = 15_00


def compute_bill(fulfillment: Fulfillment, item_total: int, mrp_total: int) -> Bill:
    delivery_fee = handling_fee = small_cart_fee = 0
    threshold = remaining = None

    if item_total > 0 and fulfillment == Fulfillment.DELIVERY:
        threshold = FREE_DELIVERY_THRESHOLD
        remaining = max(0, FREE_DELIVERY_THRESHOLD - item_total)
        delivery_fee = DELIVERY_FEE if item_total < FREE_DELIVERY_THRESHOLD else 0
        small_cart_fee = SMALL_CART_FEE if item_total < SMALL_CART_THRESHOLD else 0
        handling_fee = HANDLING_FEE
    elif item_total > 0 and fulfillment == Fulfillment.PICKUP:
        # Pickup saves the rider cost, so only the packing/handling fee applies.
        handling_fee = HANDLING_FEE
    # In-store shopping: the customer picks items themselves, no fees.

    return Bill(
        item_total_paise=item_total,
        mrp_total_paise=mrp_total,
        savings_paise=max(0, mrp_total - item_total),
        delivery_fee_paise=delivery_fee,
        handling_fee_paise=handling_fee,
        small_cart_fee_paise=small_cart_fee,
        total_paise=item_total + delivery_fee + handling_fee + small_cart_fee,
        free_delivery_threshold_paise=threshold,
        amount_to_free_delivery_paise=remaining,
    )
