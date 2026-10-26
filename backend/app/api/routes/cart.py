from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.cart import QuoteIn, QuoteOut
from app.services.pricing import build_quote
from app.services.stores import get_store

router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("/quote", response_model=QuoteOut)
def quote(body: QuoteIn, db: DbSession):
    """Prices a cart for a store and fulfillment type. Works without logging in."""
    return build_quote(db, get_store(db, body.store_id), body.fulfillment_type, body.items)
