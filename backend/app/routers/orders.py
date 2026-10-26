from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order, User
from ..schemas import OrderCreate, OrderOut
from ..security import get_current_user
from ..services.orders import cancel_order, create_order, serialize_order

router = APIRouter(prefix="/orders", tags=["orders"])


def _own_order(db: Session, user: User, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None or order.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def place_order(body: OrderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize_order(db, create_order(db, user, body))


@router.get("", response_model=list[OrderOut])
def my_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    orders = db.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.id.desc()).limit(50))
    return [serialize_order(db, o) for o in orders]


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize_order(db, _own_order(db, user, order_id))


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize_order(db, cancel_order(db, _own_order(db, user, order_id)))
