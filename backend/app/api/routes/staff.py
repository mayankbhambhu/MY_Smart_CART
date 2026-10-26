from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import DbSession, StaffUser
from app.core.errors import AppError, NotFound
from app.models import FulfillmentType, Order, User, UserRole
from app.models.enums import FINAL_STATUSES
from app.schemas.order import CompleteIn, OrderOut, StatusUpdateIn
from app.schemas.store import StoreOut
from app.services.orders import complete_order, order_out, simulate_progress, staff_set_status
from app.services.stores import get_store, store_out

router = APIRouter(prefix="/staff", tags=["staff"])


def _scope_store_id(staff: User, store_id: int | None) -> int | None:
    """Store staff only ever see their own store; admins can pick one (or see all)."""
    if staff.role == UserRole.ADMIN:
        return store_id
    if staff.store_id is None:
        raise AppError(403, "Your staff account isn't linked to a store")
    return staff.store_id


def _store_order(db: DbSession, staff: User, order_id: int) -> Order:
    order = db.get(Order, order_id)
    scope = _scope_store_id(staff, None)
    if order is None or (scope is not None and order.store_id != scope):
        raise NotFound("Order")
    return order


@router.get("/store", response_model=StoreOut | None)
def my_store(staff: StaffUser, db: DbSession):
    scope = _scope_store_id(staff, None)
    return store_out(get_store(db, scope)) if scope is not None else None


@router.get("/orders", response_model=list[OrderOut])
def store_orders(
    staff: StaffUser,
    db: DbSession,
    fulfillment_type: FulfillmentType | None = None,
    active_only: bool = True,
    store_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    stmt = select(Order).order_by(Order.created_at.desc()).limit(limit)
    scope = _scope_store_id(staff, store_id)
    if scope is not None:
        stmt = stmt.where(Order.store_id == scope)
    if fulfillment_type is not None:
        stmt = stmt.where(Order.fulfillment_type == fulfillment_type)
    orders = list(db.scalars(stmt))
    for order in orders:
        simulate_progress(db, order)
    if active_only:
        orders = [o for o in orders if o.status not in FINAL_STATUSES]
    return [order_out(o, for_staff=True) for o in orders]


@router.get("/orders/lookup", response_model=OrderOut)
def lookup_order(staff: StaffUser, db: DbSession, code: str = Query(min_length=4, max_length=16)):
    """Find an order by the code on the customer's screen / QR (e.g. SC7K3M9Q)."""
    normalized = code.strip().upper().replace("-", "").replace(" ", "")
    order = db.scalars(select(Order).where(Order.code == normalized)).first()
    scope = _scope_store_id(staff, None)
    if order is None or (scope is not None and order.store_id != scope):
        raise NotFound("Order")
    simulate_progress(db, order)
    return order_out(order, for_staff=True)


@router.post("/orders/{order_id}/status", response_model=OrderOut)
def update_status(order_id: int, body: StatusUpdateIn, staff: StaffUser, db: DbSession):
    order = _store_order(db, staff, order_id)
    staff_set_status(db, order, body.status, body.note)
    return order_out(order, for_staff=True)


@router.post("/orders/{order_id}/complete", response_model=OrderOut)
def complete(order_id: int, body: CompleteIn, staff: StaffUser, db: DbSession):
    """Pickup: verify the customer's PIN and hand over. In-store: payment received at counter."""
    order = _store_order(db, staff, order_id)
    complete_order(db, order, body.pin)
    return order_out(order, for_staff=True)
