"""Order lifecycle for all three ways of shopping: delivery, scheduled pickup and in-store."""

import hmac
import secrets
from datetime import datetime, timedelta

from sqlalchemy import case, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import generate_numeric_code
from app.core.types import to_money, utcnow
from app.models import (
    Address,
    FulfillmentType,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusEvent,
    PaymentMethod,
    PaymentStatus,
    Store,
    StoreInventory,
    User,
)
from app.models.enums import FINAL_STATUSES
from app.schemas.cart import CartLineIn
from app.schemas.catalog import ShelfLocation
from app.schemas.order import (
    CustomerOut,
    OrderItemOut,
    OrderOut,
    OrderStoreOut,
    OrderSummary,
    TimelineStep,
)
from app.schemas.store import PickupSlot
from app.services.catalog import location_label
from app.services.pricing import compute_bill, price_lines
from app.services.stores import delivery_eta_minutes, haversine_km, is_open

S = OrderStatus
F = FulfillmentType

STATUS_LABELS = {
    S.PLACED: "Order placed",
    S.CONFIRMED: "Order confirmed",
    S.PACKING: "Packing your items",
    S.OUT_FOR_DELIVERY: "Out for delivery",
    S.DELIVERED: "Delivered",
    S.READY_FOR_PICKUP: "Ready for pickup",
    S.PICKED_UP: "Picked up",
    S.AWAITING_PAYMENT: "Pay at the counter",
    S.COMPLETED: "Paid",
    S.CANCELLED: "Cancelled",
}

FLOWS = {
    F.DELIVERY: [S.PLACED, S.CONFIRMED, S.PACKING, S.OUT_FOR_DELIVERY, S.DELIVERED],
    F.PICKUP: [S.PLACED, S.CONFIRMED, S.PACKING, S.READY_FOR_PICKUP, S.PICKED_UP],
    F.IN_STORE: [S.AWAITING_PAYMENT, S.COMPLETED],
}

# Moves a store team can make from the dashboard. Handing over a pickup order (PIN check) and taking
# payment for an in-store bill go through complete_order instead.
STAFF_TRANSITIONS = {
    F.DELIVERY: {
        S.PLACED: {S.CONFIRMED, S.CANCELLED},
        S.CONFIRMED: {S.PACKING, S.CANCELLED},
        S.PACKING: {S.OUT_FOR_DELIVERY, S.CANCELLED},
        S.OUT_FOR_DELIVERY: {S.DELIVERED},
    },
    F.PICKUP: {
        S.PLACED: {S.CONFIRMED, S.CANCELLED},
        S.CONFIRMED: {S.PACKING, S.CANCELLED},
        S.PACKING: {S.READY_FOR_PICKUP, S.CANCELLED},
        S.READY_FOR_PICKUP: {S.CANCELLED},
    },
    F.IN_STORE: {S.AWAITING_PAYMENT: {S.CANCELLED}},
}

CUSTOMER_CANCELLABLE = {
    F.DELIVERY: {S.PLACED, S.CONFIRMED},
    F.PICKUP: {S.PLACED, S.CONFIRMED, S.PACKING},
    F.IN_STORE: {S.AWAITING_PAYMENT},
}

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_order_code(db: Session) -> str:
    while True:
        code = "SC" + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
        if db.scalar(select(Order.id).where(Order.code == code)) is None:
            return code


def _reserves_stock(order: Order) -> bool:
    """Delivery and pickup orders take stock when placed; in-store bills only when paid."""
    return order.fulfillment_type != F.IN_STORE


def _take_stock(db: Session, store_id: int, product_id: int, quantity: int, name: str) -> None:
    result = db.execute(
        update(StoreInventory)
        .where(
            StoreInventory.store_id == store_id,
            StoreInventory.product_id == product_id,
            StoreInventory.stock >= quantity,
        )
        .values(stock=StoreInventory.stock - quantity)
    )
    if result.rowcount != 1:
        db.rollback()
        raise AppError(409, f"{name} just went out of stock. Please update your cart.")


def _consume_stock_best_effort(db: Session, order: Order) -> None:
    """Items already scanned at the counter: decrement without ever going below zero."""
    for item in order.items:
        db.execute(
            update(StoreInventory)
            .where(
                StoreInventory.store_id == order.store_id,
                StoreInventory.product_id == item.product_id,
            )
            .values(
                stock=case(
                    (StoreInventory.stock >= item.quantity, StoreInventory.stock - item.quantity),
                    else_=0,
                )
            )
        )


def _restock(db: Session, order: Order) -> None:
    for item in order.items:
        db.execute(
            update(StoreInventory)
            .where(
                StoreInventory.store_id == order.store_id,
                StoreInventory.product_id == item.product_id,
            )
            .values(stock=StoreInventory.stock + item.quantity)
        )


def apply_status(
    db: Session, order: Order, status: OrderStatus, at: datetime | None = None, note: str | None = None
) -> None:
    order.status = status
    order.events.append(OrderStatusEvent(status=status, note=note, created_at=at or utcnow()))
    if status in (S.DELIVERED, S.PICKED_UP, S.COMPLETED):
        order.payment_status = PaymentStatus.PAID
    if status == S.CANCELLED:
        if _reserves_stock(order):
            _restock(db, order)
        if order.payment_status == PaymentStatus.PAID:
            order.payment_status = PaymentStatus.REFUNDED


def create_order(
    db: Session,
    *,
    user: User,
    store: Store,
    fulfillment: FulfillmentType,
    items: list[CartLineIn],
    payment_method: PaymentMethod,
    address: Address | None = None,
    slot: PickupSlot | None = None,
    notes: str | None = None,
) -> Order:
    if fulfillment == F.DELIVERY:
        if not store.supports_delivery:
            raise AppError(422, f"{store.name} doesn't deliver")
        if not is_open(store):
            raise AppError(409, f"{store.name} is closed right now. Try scheduling a pickup instead.")
        if address is None:
            raise AppError(422, "Please choose a delivery address")
        distance = haversine_km(address.lat, address.lng, store.lat, store.lng)
        if distance > store.delivery_radius_km:
            raise AppError(422, f"{store.name} doesn't deliver to this address yet")
        if payment_method == PaymentMethod.PAY_AT_STORE:
            raise AppError(422, "Pay at store is only available for pickup orders")
    elif fulfillment == F.PICKUP:
        if slot is None:
            raise AppError(422, "Please choose a pickup slot")
        if payment_method == PaymentMethod.COD:
            raise AppError(422, "Choose 'Pay at store' or pay online for pickup orders")
    elif payment_method == PaymentMethod.COD:
        raise AppError(422, "Pay at the counter or online for in-store purchases")

    lines, ctx = price_lines(db, store.id, items, enforce_stock=fulfillment != F.IN_STORE)
    problems = [
        f"{line.product.name if line.product else 'An item'}: {line.issue}" for line in lines if line.issue
    ]
    if problems:
        raise AppError(409, "Some items in your cart are unavailable", {"issues": problems})

    if fulfillment != F.IN_STORE:
        for line in lines:
            _take_stock(db, store.id, line.product_id, line.quantity, line.product.name)

    item_total = sum((line.line_total for line in lines), start=to_money(0))
    mrp_total = sum((line.line_mrp_total for line in lines), start=to_money(0))
    bill = compute_bill(item_total, mrp_total, fulfillment)

    order = Order(
        code=new_order_code(db),
        user_id=user.id,
        store_id=store.id,
        fulfillment_type=fulfillment,
        payment_method=payment_method,
        payment_status=PaymentStatus.PENDING,
        item_total=bill.item_total,
        mrp_total=bill.mrp_total,
        delivery_fee=bill.delivery_fee,
        handling_fee=bill.handling_fee,
        small_cart_fee=bill.small_cart_fee,
        grand_total=bill.grand_total,
        notes=notes,
    )
    if fulfillment == F.DELIVERY:
        order.delivery_address = {
            "label": address.label,
            "receiver_name": address.receiver_name,
            "receiver_phone": address.receiver_phone,
            "line": address.one_line(),
            "lat": address.lat,
            "lng": address.lng,
        }
        order.eta_minutes = delivery_eta_minutes(haversine_km(address.lat, address.lng, store.lat, store.lng))
    if fulfillment == F.PICKUP:
        order.pickup_slot_start = slot.start
        order.pickup_slot_end = slot.end
        order.handover_pin = generate_numeric_code(4)

    for line in lines:
        inv = ctx.inventory.get(line.product_id)
        p = line.product
        order.items.append(
            OrderItem(
                product_id=p.id,
                name=p.name,
                unit_label=p.unit_label,
                emoji=p.emoji,
                image_url=p.image_url,
                price=p.price,
                mrp=p.mrp,
                quantity=line.quantity,
                line_total=to_money(line.line_total),
                aisle=inv.aisle if inv else None,
                row=inv.row if inv else None,
            )
        )

    db.add(order)
    if payment_method == PaymentMethod.ONLINE:
        order.payment_status = PaymentStatus.PAID  # mock gateway: payment always succeeds
    if fulfillment == F.IN_STORE:
        apply_status(db, order, S.AWAITING_PAYMENT)
        if payment_method == PaymentMethod.ONLINE:
            # Scan & go: paid in the app, so the bill is closed straight away.
            _consume_stock_best_effort(db, order)
            apply_status(db, order, S.COMPLETED, note="Paid in app")
    else:
        apply_status(db, order, S.PLACED)
    db.commit()
    return order


def cancel_by_customer(db: Session, order: Order) -> None:
    if order.status not in CUSTOMER_CANCELLABLE[F(order.fulfillment_type)]:
        raise AppError(409, "This order can no longer be cancelled")
    apply_status(db, order, S.CANCELLED, note="Cancelled by customer")
    db.commit()


def staff_set_status(db: Session, order: Order, status: OrderStatus, note: str | None) -> None:
    allowed = STAFF_TRANSITIONS[F(order.fulfillment_type)].get(S(order.status), set())
    if status not in allowed:
        raise AppError(
            409, f"Can't change a '{STATUS_LABELS[S(order.status)]}' order to '{STATUS_LABELS[status]}'"
        )
    apply_status(db, order, status, note=note)
    db.commit()


def complete_order(db: Session, order: Order, pin: str | None) -> None:
    """Hand over a pickup order (PIN check), take payment for an in-store bill, or mark delivered."""
    kind = F(order.fulfillment_type)
    if kind == F.PICKUP:
        if order.status != S.READY_FOR_PICKUP:
            raise AppError(409, "Mark the order ready for pickup first")
        if not pin or not hmac.compare_digest(pin, order.handover_pin or ""):
            raise AppError(400, "Wrong pickup PIN. Ask the customer to check their app.")
        apply_status(db, order, S.PICKED_UP, note="Handed over at counter")
    elif kind == F.IN_STORE:
        if order.status != S.AWAITING_PAYMENT:
            raise AppError(409, "This bill is already closed")
        _consume_stock_best_effort(db, order)
        apply_status(db, order, S.COMPLETED, note="Paid at counter")
    else:
        if order.status != S.OUT_FOR_DELIVERY:
            raise AppError(409, "Order isn't out for delivery yet")
        apply_status(db, order, S.DELIVERED)
    db.commit()


def simulate_progress(db: Session, order: Order, now: datetime | None = None) -> bool:
    """Demo mode: walk delivery/pickup orders through their statuses on a realistic clock.
    Pickup orders still need the PIN handover at the store to be marked picked up."""
    if not get_settings().simulate_order_progress or order.status in FINAL_STATUSES:
        return False
    now = now or utcnow()
    placed = order.created_at
    if order.fulfillment_type == F.DELIVERY:
        eta = timedelta(minutes=order.eta_minutes or 12)
        plan = [
            (S.CONFIRMED, placed + timedelta(seconds=15)),
            (S.PACKING, placed + timedelta(seconds=60)),
            (S.OUT_FOR_DELIVERY, placed + max(timedelta(minutes=2), eta * 0.4)),
            (S.DELIVERED, placed + eta),
        ]
    elif order.fulfillment_type == F.PICKUP and order.pickup_slot_start:
        slot = order.pickup_slot_start
        plan = [
            (S.CONFIRMED, placed + timedelta(seconds=15)),
            (S.PACKING, max(placed + timedelta(seconds=60), slot - timedelta(minutes=40))),
            (S.READY_FOR_PICKUP, max(placed + timedelta(minutes=3), slot - timedelta(minutes=15))),
        ]
    else:
        return False

    flow = FLOWS[F(order.fulfillment_type)]
    changed = False
    for status, at in plan:
        if now >= at and flow.index(status) > flow.index(S(order.status)):
            apply_status(db, order, status, at=at)
            changed = True
    if changed:
        db.commit()
    return changed


def build_timeline(order: Order) -> list[TimelineStep]:
    flow = FLOWS[F(order.fulfillment_type)]
    reached: dict[str, datetime] = {}
    for event in order.events:
        reached.setdefault(event.status, event.created_at)

    if order.status == S.CANCELLED:
        steps = [
            TimelineStep(status=s, label=STATUS_LABELS[s], done=True, current=False, at=reached[s])
            for s in flow
            if s in reached
        ]
        steps.append(
            TimelineStep(
                status=S.CANCELLED,
                label=STATUS_LABELS[S.CANCELLED],
                done=True,
                current=True,
                at=reached.get(S.CANCELLED),
            )
        )
        return steps

    current = flow.index(S(order.status))
    return [
        TimelineStep(
            status=s, label=STATUS_LABELS[s], done=i <= current, current=i == current, at=reached.get(s)
        )
        for i, s in enumerate(flow)
    ]


def order_out(order: Order, *, for_staff: bool = False) -> OrderOut:
    aisle_names = {a.number: a.name for a in order.store.aisles}
    items = [
        OrderItemOut(
            product_id=item.product_id,
            name=item.name,
            unit_label=item.unit_label,
            emoji=item.emoji,
            image_url=item.image_url,
            price=item.price,
            mrp=item.mrp,
            quantity=item.quantity,
            line_total=item.line_total,
            location=ShelfLocation(
                aisle=item.aisle,
                aisle_name=aisle_names.get(item.aisle),
                row=item.row,
                label=location_label(item.aisle, item.row),
            )
            if item.aisle is not None and item.row is not None
            else None,
        )
        for item in order.items
    ]
    status = S(order.status)
    return OrderOut(
        id=order.id,
        code=order.code,
        fulfillment_type=order.fulfillment_type,
        status=status,
        status_label=STATUS_LABELS[status],
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        store=OrderStoreOut.model_validate(order.store),
        delivery_address=order.delivery_address,
        eta_minutes=order.eta_minutes,
        pickup_slot_start=order.pickup_slot_start,
        pickup_slot_end=order.pickup_slot_end,
        handover_pin=None if for_staff else order.handover_pin,
        item_count=order.item_count,
        item_total=order.item_total,
        mrp_total=order.mrp_total,
        savings=order.mrp_total - order.item_total,
        delivery_fee=order.delivery_fee,
        handling_fee=order.handling_fee,
        small_cart_fee=order.small_cart_fee,
        grand_total=order.grand_total,
        notes=order.notes,
        items=items,
        timeline=build_timeline(order),
        can_cancel=status in CUSTOMER_CANCELLABLE[F(order.fulfillment_type)],
        created_at=order.created_at,
        customer=CustomerOut(name=order.user.name, phone=order.user.phone) if for_staff else None,
    )


def order_summary(order: Order) -> OrderSummary:
    status = S(order.status)
    return OrderSummary(
        id=order.id,
        code=order.code,
        fulfillment_type=order.fulfillment_type,
        status=status,
        status_label=STATUS_LABELS[status],
        store_name=order.store.name,
        item_count=order.item_count,
        grand_total=order.grand_total,
        created_at=order.created_at,
        pickup_slot_start=order.pickup_slot_start,
        preview=[item.emoji for item in order.items[:5]],
    )
