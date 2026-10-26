from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order, OrderStatus, User
from ..schemas import StaffOrderOut, VerifyCodeRequest
from ..security import require_staff
from ..services.orders import FLOWS, advance_order, next_status, serialize_staff_order

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/orders", response_model=list[StaffOrderOut])
def store_orders(
    store_id: int,
    active: bool = True,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    stmt = select(Order).where(Order.store_id == store_id).order_by(Order.id.desc()).limit(100)
    orders = db.scalars(stmt).all()
    if active:
        orders = [o for o in orders if o.status != OrderStatus.CANCELLED and o.status != FLOWS[o.fulfillment][-1]]
    return [serialize_staff_order(db, o) for o in orders]


@router.post("/orders/{order_id}/advance", response_model=StaffOrderOut)
def advance(order_id: int, _: User = Depends(require_staff), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return serialize_staff_order(db, advance_order(db, order))


@router.post("/verify-code", response_model=StaffOrderOut)
def verify_code(body: VerifyCodeRequest, _: User = Depends(require_staff), db: Session = Depends(get_db)):
    """Look up the order behind a pickup OTP or in-store bill code shown by a customer."""
    code = body.code.strip().upper()
    candidates = db.scalars(
        select(Order)
        .where(Order.store_id == body.store_id, Order.code == code, Order.status != OrderStatus.CANCELLED)
        .order_by(Order.id.desc())
        .limit(20)
    ).all()
    # Short pickup codes can repeat over time, so prefer an order that is still in progress.
    order = next((o for o in candidates if next_status(o) is not None), candidates[0] if candidates else None)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active order with that code at this store")
    return serialize_staff_order(db, order)
