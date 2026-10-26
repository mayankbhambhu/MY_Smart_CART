from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import PaymentMethod
from app.schemas.cart import CartLineIn
from app.schemas.catalog import ProductOut
from app.schemas.common import Money, Schema
from app.schemas.store import StoreOut


class ListItemIn(BaseModel):
    query: str = Field(min_length=1, max_length=80)
    quantity: int = Field(default=1, ge=1, le=50)
    # Set when the shopper picked a specific product (e.g. swapped to an alternative).
    product_id: int | None = None


class ShoppingListIn(BaseModel):
    """Either free text ("2 milk, bread, 1kg atta, maggi") — typed or spoken — or structured items."""

    text: str | None = Field(default=None, max_length=2000)
    items: list[ListItemIn] = Field(default_factory=list, max_length=60)


class ResolvedItem(Schema):
    query: str
    quantity: int
    product: ProductOut  # includes availability + shelf location
    in_stock: bool
    line_total: Money
    confidence: int
    step: int  # position on the suggested walking route
    alternatives: list[ProductOut]


class UnmatchedItem(Schema):
    query: str
    quantity: int
    suggestions: list[ProductOut]


class AisleStop(Schema):
    aisle: int
    name: str | None
    item_count: int


class ShoppingListOut(Schema):
    store: StoreOut
    layout_rows: int
    aisle_count: int
    items: list[ResolvedItem]
    unmatched: list[UnmatchedItem]
    route: list[AisleStop]
    item_count: int
    total: Money
    mrp_total: Money
    savings: Money
    out_of_stock_count: int


class InStoreCheckoutIn(BaseModel):
    items: list[CartLineIn] = Field(min_length=1, max_length=100)
    payment_method: Literal[PaymentMethod.PAY_AT_STORE, PaymentMethod.ONLINE] = PaymentMethod.PAY_AT_STORE
