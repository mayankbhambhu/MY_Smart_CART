import secrets
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    Address,
    Fulfillment,
    Inventory,
    Order,
    OrderEvent,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    Store,
    User,
)
from ..schemas import Bill, CartItemIn, OrderCreate, OrderItemOut, OrderOut, OrderStep, StaffOrderOut, StoreBrief
from .catalog import location_of, store_inventory
from .geo import delivery_eta_minutes, haversine_km, is_store_open
from .pricing import compute_bill
from .slots import validate_slot

# The happy path for each way of shopping. Staff move orders one step at a time.
FLOWS: dict[Fulfillment, list[OrderStatus]] = {
    Fulfillment.DELIVERY: [
        OrderStatus.PLACED,
        OrderStatus.PACKED,
        OrderStatus.OUT_FOR_DELIVERY,
        OrderStatus.DELIVERED,
    ],
    Fulfillment.PICKUP: [
        OrderStatus.PLACED,
        OrderStatus.PACKED,
        OrderStatus.READY_FOR_PICKUP,
        OrderStatus.PICKED_UP,
    ],
    Fulfillment.IN_STORE: [OrderStatus.AWAITING_PAYMENT, OrderStatus.COMPLETED],
}

STATUS_LABELS: dict[OrderStatus, str] = {
    OrderStatus.PLACED: "Order placed",
    OrderStatus.PACKED: "Packed",
    OrderStatus.OUT_FOR_DELIVERY: "Out for delivery",
    OrderStatus.DELIVERED: "Delivered",
    OrderStatus.READY_FOR_PICKUP: "Ready for pickup",
    OrderStatus.PICKED_UP: "Picked up",
    OrderStatus.AWAITING_PAYMENT: "Pay at counter",
    OrderStatus.COMPLETED: "Completed",
    OrderStatus.CANCELLED: "Cancelled",
}

# No 0/O or 1/I so codes are easy to read aloud at the counter.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


@dataclass
class Line:
    inventory: Inventory | None
    product_id: int
    quantity: int

    @property
    def available(self) -> int:
        return self.inventory.stock if self.inventory else 0


def resolve_lines(
    db: Session, store_id: int, items: list[CartItemIn], lock: bool = False
) -> tuple[list[Line], list[str]]:
    """Merge duplicate items, attach store inventory and collect stock problems."""
    quantities: dict[int, int] = {}
    for item in items:
        quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity

    inventory = store_inventory(db, store_id, quantities.keys(), lock=lock)
    lines: list[Line] = []
    issues: list[str] = []
    for product_id, quantity in quantities.items():
        inv = inventory.get(product_id)
        line = Line(inventory=inv, product_id=product_id, quantity=quantity)
        if inv is None:
            issues.append(f"Product #{product_id} is not sold at this store")
            continue
        if inv.stock <= 0:
            issues.append(f"{inv.product.name} is out of stock")
        elif inv.stock < quantity:
            issues.append(f"Only {inv.stock} × {inv.product.name} left in stock")
        lines.append(line)
    return lines, issues


def totals(lines: list[Line]) -> tuple[int, int]:
    item_total = sum(line.inventory.product.price_paise * line.quantity for line in lines if line.inventory)
    mrp_total = sum(line.inventory.product.mrp_paise * line.quantity for line in lines if line.inventory)
    return item_total, mrp_total


def _random_code(fulfillment: Fulfillment) -> str | None:
    if fulfillment == Fulfillment.PICKUP:
        return f"{secrets.randbelow(10**4):04d}"
    if fulfillment == Fulfillment.IN_STORE:
        return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
    return None


def _new_code(db: Session, store_id: int, fulfillment: Fulfillment) -> str | None:
    """A code that no other in-progress order at this store is using."""
    open_statuses = [s for flow in FLOWS.values() for s in flow[:-1]]
    for _ in range(20):
        code = _random_code(fulfillment)
        if code is None:
            return None
        clash = db.scalars(
            select(Order.id).where(Order.store_id == store_id, Order.code == code, Order.status.in_(open_statuses))
        ).first()
        if clash is None:
            return code
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Could not allocate an order code, please retry")


def _format_address(address: Address) -> str:
    parts = [address.line1, address.line2, address.landmark, f"{address.city} - {address.pincode}"]
    return ", ".join(p for p in parts if p)


def _add_event(order: Order, new_status: OrderStatus) -> None:
    order.status = new_status
    order.events.append(OrderEvent(status=new_status))


def create_order(db: Session, user: User, payload: OrderCreate) -> Order:
    store = db.get(Store, payload.store_id)
    if store is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Store not found")

    # Lock the stock rows (on Postgres/MySQL) so two orders can't oversell the same item.
    lines, issues = resolve_lines(db, store.id, payload.items, lock=True)
    if issues:
        raise HTTPException(status.HTTP_409_CONFLICT, "; ".join(issues))

    order = Order(
        user_id=user.id,
        store_id=store.id,
        fulfillment=payload.fulfillment,
        payment_method=payload.payment_method,
        notes=payload.notes,
        code=_new_code(db, store.id, payload.fulfillment),
    )

    if payload.fulfillment == Fulfillment.DELIVERY:
        if not is_store_open(store):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{store.name} is closed right now")
        if payload.address_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose a delivery address")
        address = db.get(Address, payload.address_id)
        if address is None or address.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Address not found")
        distance = haversine_km(store.lat, store.lng, address.lat, address.lng)
        if distance > store.delivery_radius_km:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{store.name} doesn't deliver to this address yet")
        order.address_id = address.id
        order.delivery_address = _format_address(address)
        order.eta_minutes = delivery_eta_minutes(distance)
    elif payload.fulfillment == Fulfillment.PICKUP:
        if payload.pickup_slot_start is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose a pickup slot")
        order.pickup_slot_start, order.pickup_slot_end = validate_slot(db, store, payload.pickup_slot_start)
    elif payload.fulfillment == Fulfillment.IN_STORE:
        if not is_store_open(store):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{store.name} is closed right now")

    item_total, mrp_total = totals(lines)
    bill = compute_bill(payload.fulfillment, item_total, mrp_total)
    order.item_total_paise = bill.item_total_paise
    order.mrp_total_paise = bill.mrp_total_paise
    order.delivery_fee_paise = bill.delivery_fee_paise
    order.handling_fee_paise = bill.handling_fee_paise
    order.small_cart_fee_paise = bill.small_cart_fee_paise
    order.total_paise = bill.total_paise

    for line in lines:
        product = line.inventory.product
        line.inventory.stock -= line.quantity
        order.items.append(
            OrderItem(
                product_id=product.id,
                name=product.name,
                unit=product.unit,
                emoji=product.emoji,
                price_paise=product.price_paise,
                mrp_paise=product.mrp_paise,
                quantity=line.quantity,
            )
        )

    online = payload.payment_method in (PaymentMethod.UPI, PaymentMethod.CARD)
    # Online payments are simulated: treat them as captured immediately.
    order.payment_status = PaymentStatus.PAID if online else PaymentStatus.PENDING
    _add_event(order, FLOWS[payload.fulfillment][0])
    if payload.fulfillment == Fulfillment.IN_STORE and online:
        # Scan & go: already paid in the app, so the bill code works as an exit pass.
        _add_event(order, OrderStatus.COMPLETED)

    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def next_status(order: Order) -> OrderStatus | None:
    flow = FLOWS[order.fulfillment]
    if order.status not in flow:
        return None
    index = flow.index(order.status)
    return flow[index + 1] if index + 1 < len(flow) else None


def can_cancel(order: Order) -> bool:
    return order.status == FLOWS[order.fulfillment][0]


def advance_order(db: Session, order: Order) -> Order:
    target = next_status(order)
    if target is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order is already complete")
    _add_event(order, target)
    if target == FLOWS[order.fulfillment][-1]:
        order.payment_status = PaymentStatus.PAID  # cash is collected on handover
    db.commit()
    db.refresh(order)
    return order


def cancel_order(db: Session, order: Order) -> Order:
    if not can_cancel(order):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This order can no longer be cancelled")
    inventory = store_inventory(db, order.store_id, [item.product_id for item in order.items])
    for item in order.items:
        if item.product_id in inventory:
            inventory[item.product_id].stock += item.quantity
    if order.payment_status == PaymentStatus.PAID:
        order.payment_status = PaymentStatus.REFUNDED
    _add_event(order, OrderStatus.CANCELLED)
    db.commit()
    db.refresh(order)
    return order


def serialize_order(db: Session, order: Order) -> OrderOut:
    inventory = store_inventory(db, order.store_id, [item.product_id for item in order.items])
    items = [
        OrderItemOut(
            product_id=item.product_id,
            name=item.name,
            unit=item.unit,
            emoji=item.emoji,
            price_paise=item.price_paise,
            mrp_paise=item.mrp_paise,
            quantity=item.quantity,
            location=location_of(inventory[item.product_id]) if item.product_id in inventory else None,
        )
        for item in order.items
    ]

    reached = {event.status: event.created_at for event in order.events}
    steps = [
        OrderStep(status=s, label=STATUS_LABELS[s], done=s in reached, at=reached.get(s))
        for s in FLOWS[order.fulfillment]
    ]
    if order.status == OrderStatus.CANCELLED:
        steps = [step for step in steps if step.done]
        steps.append(
            OrderStep(
                status=OrderStatus.CANCELLED,
                label=STATUS_LABELS[OrderStatus.CANCELLED],
                done=True,
                at=reached[OrderStatus.CANCELLED],
            )
        )

    return OrderOut(
        id=order.id,
        store=StoreBrief.model_validate(order.store),
        fulfillment=order.fulfillment,
        status=order.status,
        status_label=STATUS_LABELS[order.status],
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        delivery_address=order.delivery_address,
        eta_minutes=order.eta_minutes,
        pickup_slot_start=order.pickup_slot_start,
        pickup_slot_end=order.pickup_slot_end,
        code=order.code,
        notes=order.notes,
        bill=Bill(
            item_total_paise=order.item_total_paise,
            mrp_total_paise=order.mrp_total_paise,
            savings_paise=max(0, order.mrp_total_paise - order.item_total_paise),
            delivery_fee_paise=order.delivery_fee_paise,
            handling_fee_paise=order.handling_fee_paise,
            small_cart_fee_paise=order.small_cart_fee_paise,
            total_paise=order.total_paise,
        ),
        items=items,
        steps=steps,
        can_cancel=can_cancel(order),
        created_at=order.created_at,
    )


def serialize_staff_order(db: Session, order: Order) -> StaffOrderOut:
    base = serialize_order(db, order)
    upcoming = next_status(order)
    return StaffOrderOut(
        **base.model_dump(),
        customer_phone=order.user.phone,
        customer_name=order.user.name,
        next_status=upcoming,
        next_status_label=STATUS_LABELS[upcoming] if upcoming else None,
    )

