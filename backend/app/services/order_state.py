"""Low-level order state changes shared by the order and payment services.

Status changes use a conditional UPDATE ("only if it's still in the state I read"), so a customer,
the store team, a payment webhook and the expiry job can't trample each other's changes."""

from datetime import datetime

from sqlalchemy import case, inspect, update
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.types import utcnow
from app.models import FulfillmentType, Order, OrderStatus, OrderStatusEvent, PaymentStatus, StoreInventory

S = OrderStatus


def reserves_stock(order: Order) -> bool:
    """Delivery and pickup orders take stock when placed; in-store bills only when paid."""
    return order.fulfillment_type != FulfillmentType.IN_STORE


def take_stock(db: Session, store_id: int, product_id: int, quantity: int, name: str) -> None:
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


def consume_stock_best_effort(db: Session, order: Order) -> None:
    """Items already in the shopper's hands: decrement without ever going below zero."""
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


def restock(db: Session, order: Order) -> None:
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
    """Moves an order to `status` (and does its side effects). Doesn't commit.

    Raises a 409 if somebody else changed the order since it was loaded."""
    previous = order.status
    if inspect(order).persistent:
        claimed = db.execute(
            update(Order)
            .where(Order.id == order.id, Order.status == previous)
            .values(status=status)
            .execution_options(synchronize_session=False)
        ).rowcount
        if claimed != 1:
            db.rollback()
            raise AppError(409, "This order was just updated. Please refresh and try again.")
    order.status = status
    order.events.append(OrderStatusEvent(status=status, note=note, created_at=at or utcnow()))
    if status in (S.DELIVERED, S.PICKED_UP, S.COMPLETED):
        order.payment_status = PaymentStatus.PAID
    if status == S.CANCELLED and reserves_stock(order):
        restock(db, order)
