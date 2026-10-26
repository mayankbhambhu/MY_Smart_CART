from pydantic import BaseModel, Field

from app.models.enums import FulfillmentType
from app.schemas.catalog import ProductOut
from app.schemas.common import Money, Schema


class CartLineIn(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=50)


class QuoteIn(BaseModel):
    store_id: int
    fulfillment_type: FulfillmentType = FulfillmentType.DELIVERY
    items: list[CartLineIn] = Field(default_factory=list, max_length=100)


class Bill(Schema):
    item_total: Money
    mrp_total: Money
    savings: Money
    delivery_fee: Money
    handling_fee: Money
    small_cart_fee: Money
    grand_total: Money


class QuoteLine(Schema):
    product: ProductOut
    requested_quantity: int
    quantity: int  # what the store can actually supply
    line_total: Money
    line_mrp_total: Money
    issue: str | None = None


class QuoteOut(Schema):
    store_id: int
    fulfillment_type: FulfillmentType
    lines: list[QuoteLine]
    item_count: int
    bill: Bill
    free_delivery_gap: Money | None = None
    notes: list[str]
    can_checkout: bool
    blocking_issues: list[str]
    # Ids the client should drop from its cart (deleted or deactivated products).
    unavailable_product_ids: list[int] = []
