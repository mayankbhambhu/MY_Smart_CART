from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import NotFound
from app.models import Address, FulfillmentType, Order, User
from app.schemas.order import OrderCreate, OrderOut, OrderSummary
from app.services import payments
from app.services.orders import cancel_by_customer, create_order, order_out, order_summary, simulate_progress
from app.services.slots import resolve_pickup_slot
from app.services.stores import get_store

router = APIRouter(prefix="/orders", tags=["orders"])


def own_order(db: DbSession, user: User, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None or order.user_id != user.id:
        raise NotFound("Order")
    return order


def _refresh(db: DbSession, order: Order) -> None:
    """Brings an order up to date before showing it: payment expiry, then demo progress."""
    payments.expire_if_overdue(db, order)
    simulate_progress(db, order)


@router.post("", response_model=OrderOut, status_code=201)
def place_order(body: OrderCreate, user: CurrentUser, db: DbSession):
    store = get_store(db, body.store_id)
    address = slot = None
    if body.fulfillment_type == FulfillmentType.DELIVERY and body.address_id is not None:
        address = db.get(Address, body.address_id)
        if address is None or address.user_id != user.id:
            raise NotFound("Address")
    if body.fulfillment_type == FulfillmentType.PICKUP and body.pickup_slot_start is not None:
        slot = resolve_pickup_slot(db, store, body.pickup_slot_start)
    order = create_order(
        db,
        user=user,
        store=store,
        fulfillment=body.fulfillment_type,
        items=body.items,
        payment_method=body.payment_method,
        address=address,
        slot=slot,
        notes=body.notes,
    )
    return order_out(order)


@router.get("", response_model=list[OrderSummary])
def my_orders(user: CurrentUser, db: DbSession, limit: int = Query(default=50, ge=1, le=200)):
    orders = list(
        db.scalars(
            select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc()).limit(limit)
        )
    )
    for order in orders:
        _refresh(db, order)
    return [order_summary(o) for o in orders]


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, user: CurrentUser, db: DbSession):
    order = own_order(db, user, order_id)
    _refresh(db, order)
    return order_out(order)


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, user: CurrentUser, db: DbSession):
    order = own_order(db, user, order_id)
    _refresh(db, order)
    cancel_by_customer(db, order)
    return order_out(order)
