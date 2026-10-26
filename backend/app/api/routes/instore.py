from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.core.errors import AppError
from app.models import FulfillmentType
from app.schemas.instore import InStoreCheckoutIn, ShoppingListIn, ShoppingListOut
from app.schemas.order import OrderOut
from app.services.instore import resolve_shopping_list
from app.services.orders import create_order, order_out
from app.services.stores import get_store

router = APIRouter(prefix="/instore", tags=["in-store"])


def _instore_store(db: DbSession, store_id: int):
    store = get_store(db, store_id)
    if not store.supports_instore:
        raise AppError(422, f"{store.name} doesn't support in-store shopping in the app yet")
    return store


@router.post("/{store_id}/resolve", response_model=ShoppingListOut)
def resolve_list(store_id: int, body: ShoppingListIn, db: DbSession):
    """Finds each requested item in this store: product match, aisle/row, price, and the total.

    Send `text` for a typed or spoken list ("2 milk, bread, 1kg atta, maggi") and/or `items`
    for structured entries. Works without logging in."""
    if not (body.text and body.text.strip()) and not body.items:
        raise AppError(422, "Tell us what you want to buy")
    return resolve_shopping_list(db, _instore_store(db, store_id), body)


@router.post("/{store_id}/checkout", response_model=OrderOut, status_code=201)
def checkout(store_id: int, body: InStoreCheckoutIn, user: CurrentUser, db: DbSession):
    """Creates the in-store bill. Pay at the counter (cashier scans the bill QR) or pay in the app."""
    order = create_order(
        db,
        user=user,
        store=_instore_store(db, store_id),
        fulfillment=FulfillmentType.IN_STORE,
        items=body.items,
        payment_method=body.payment_method,
    )
    return order_out(order)
