"""Server-side bill calculation. The client only ever sends product ids and quantities."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.types import to_money
from app.models import FulfillmentType, Product, Store
from app.schemas.cart import Bill, CartLineIn, QuoteLine, QuoteOut
from app.services.catalog import StoreContext, product_out
from app.services.stores import is_open

ZERO = Decimal(0)


def inr(amount: Decimal) -> str:
    amount = to_money(amount)
    return f"₹{amount:.0f}" if amount == amount.to_integral_value() else f"₹{amount:.2f}"


def compute_bill(item_total: Decimal, mrp_total: Decimal, fulfillment: FulfillmentType) -> Bill:
    s = get_settings()
    delivery_fee = handling_fee = small_cart_fee = ZERO
    if item_total > 0 and fulfillment == FulfillmentType.DELIVERY:
        if item_total < s.free_delivery_threshold:
            delivery_fee = s.delivery_fee
        if item_total < s.small_cart_threshold:
            small_cart_fee = s.small_cart_fee
    if item_total > 0 and fulfillment in (FulfillmentType.DELIVERY, FulfillmentType.PICKUP):
        handling_fee = s.handling_fee
    return Bill(
        item_total=to_money(item_total),
        mrp_total=to_money(mrp_total),
        savings=to_money(mrp_total - item_total),
        delivery_fee=to_money(delivery_fee),
        handling_fee=to_money(handling_fee),
        small_cart_fee=to_money(small_cart_fee),
        grand_total=to_money(item_total + delivery_fee + handling_fee + small_cart_fee),
    )


@dataclass
class PricedLine:
    product_id: int
    product: Product | None
    requested: int
    quantity: int
    issue: str | None

    @property
    def line_total(self) -> Decimal:
        return self.product.price * self.quantity if self.product else ZERO

    @property
    def line_mrp_total(self) -> Decimal:
        return self.product.mrp * self.quantity if self.product else ZERO


def price_lines(
    db: Session, store_id: int, items: list[CartLineIn], enforce_stock: bool = True
) -> tuple[list[PricedLine], StoreContext]:
    """Merges duplicate lines and checks each one against the store's stock.

    In-store purchases pass enforce_stock=False: the shopper is already holding the item, so only
    "does this store sell it" matters, not what the system thinks is on the shelf."""
    max_qty = get_settings().max_qty_per_item
    merged: dict[int, int] = {}
    for item in items:
        merged[item.product_id] = merged.get(item.product_id, 0) + item.quantity

    products = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(merged)))}
    ctx = StoreContext.load(db, store_id, merged.keys())

    lines: list[PricedLine] = []
    for product_id, requested in merged.items():
        product = products.get(product_id)
        if product is None or not product.is_active:
            lines.append(PricedLine(product_id, None, requested, 0, "No longer available"))
            continue
        if product_id not in ctx.inventory:
            lines.append(PricedLine(product_id, product, requested, 0, "Not sold at this store"))
            continue
        if not enforce_stock:
            lines.append(PricedLine(product_id, product, requested, requested, None))
            continue
        stock = ctx.stock_of(product_id)
        cap = min(stock, max_qty)
        if stock <= 0:
            lines.append(PricedLine(product_id, product, requested, 0, "Out of stock"))
        elif requested > cap:
            issue = f"Only {cap} left" if cap == stock else f"Max {cap} per order"
            lines.append(PricedLine(product_id, product, requested, cap, issue))
        else:
            lines.append(PricedLine(product_id, product, requested, requested, None))
    return lines, ctx


def build_quote(db: Session, store: Store, fulfillment: FulfillmentType, items: list[CartLineIn]) -> QuoteOut:
    s = get_settings()
    lines, ctx = price_lines(db, store.id, items)

    quote_lines: list[QuoteLine] = []
    unavailable: list[str] = []
    item_total = mrp_total = ZERO
    item_count = 0
    for line in lines:
        if line.product is None:
            unavailable.append("An item in your cart is no longer sold")
            continue
        item_total += line.line_total
        mrp_total += line.line_mrp_total
        item_count += line.quantity
        quote_lines.append(
            QuoteLine(
                product=product_out(line.product, ctx),
                requested_quantity=line.requested,
                quantity=line.quantity,
                line_total=to_money(line.line_total),
                line_mrp_total=to_money(line.line_mrp_total),
                issue=line.issue,
            )
        )

    bill = compute_bill(item_total, mrp_total, fulfillment)
    notes: list[str] = []
    free_delivery_gap = None
    if fulfillment == FulfillmentType.DELIVERY and 0 < item_total < s.free_delivery_threshold:
        free_delivery_gap = to_money(s.free_delivery_threshold - item_total)
        notes.append(f"Add items worth {inr(free_delivery_gap)} more for FREE delivery")
    if fulfillment == FulfillmentType.PICKUP and item_total > 0:
        would_pay = compute_bill(item_total, mrp_total, FulfillmentType.DELIVERY)
        saved = would_pay.grand_total - bill.grand_total
        if saved > 0:
            notes.append(f"Picking up saves you {inr(saved)} in delivery charges")
    if bill.savings > 0:
        notes.append(f"You're saving {inr(bill.savings)} on this order")

    blocking: list[str] = []
    if item_count == 0 and not unavailable:
        blocking.append("Your cart is empty")
    if fulfillment == FulfillmentType.DELIVERY and not store.supports_delivery:
        blocking.append(f"{store.name} doesn't deliver")
    if fulfillment == FulfillmentType.PICKUP and not store.supports_pickup:
        blocking.append(f"{store.name} doesn't offer pickup")
    if fulfillment == FulfillmentType.DELIVERY and not is_open(store):
        blocking.append(f"{store.name} is closed right now. Try scheduling a pickup instead.")
    if unavailable or any(line.issue for line in quote_lines):
        blocking.append("Some items are unavailable. Update your cart to continue.")

    return QuoteOut(
        store_id=store.id,
        fulfillment_type=fulfillment,
        lines=quote_lines,
        item_count=item_count,
        bill=bill,
        free_delivery_gap=free_delivery_gap,
        notes=notes,
        can_checkout=not blocking,
        blocking_issues=blocking,
        unavailable_product_ids=[line.product_id for line in lines if line.product is None],
    )
