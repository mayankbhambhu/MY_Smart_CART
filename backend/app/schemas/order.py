from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import FulfillmentType, OrderStatus, PaymentMethod, PaymentStatus
from app.schemas.cart import CartLineIn
from app.schemas.catalog import ShelfLocation
from app.schemas.common import Money, Schema
from app.schemas.payment import PaymentInfo


class OrderCreate(BaseModel):
    store_id: int
    fulfillment_type: Literal[FulfillmentType.DELIVERY, FulfillmentType.PICKUP]
    items: list[CartLineIn] = Field(min_length=1, max_length=100)
    payment_method: PaymentMethod
    address_id: int | None = None  # required for delivery
    pickup_slot_start: datetime | None = None  # required for pickup
    notes: str | None = Field(default=None, max_length=300)


class OrderStoreOut(Schema):
    id: int
    name: str
    address: str
    phone: str | None
    lat: float
    lng: float


class OrderItemOut(Schema):
    product_id: int
    name: str
    unit_label: str
    emoji: str
    image_url: str | None
    price: Money
    mrp: Money
    quantity: int
    line_total: Money
    location: ShelfLocation | None = None


class TimelineStep(Schema):
    status: OrderStatus
    label: str
    done: bool
    current: bool
    at: datetime | None = None


class CustomerOut(Schema):
    name: str | None
    phone: str


class OrderOut(Schema):
    id: int
    code: str
    fulfillment_type: FulfillmentType
    status: OrderStatus
    status_label: str
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    payment_due: bool = False  # online payment still to be made (see payment_expires_at)
    payment_expires_at: datetime | None = None
    payment: PaymentInfo | None = None  # latest online payment, if any
    store: OrderStoreOut
    delivery_address: dict | None
    eta_minutes: int | None
    pickup_slot_start: datetime | None
    pickup_slot_end: datetime | None
    # Shown to the customer only; staff must ask the customer for it at handover.
    handover_pin: str | None = None
    item_count: int
    item_total: Money
    mrp_total: Money
    savings: Money
    delivery_fee: Money
    handling_fee: Money
    small_cart_fee: Money
    grand_total: Money
    notes: str | None
    items: list[OrderItemOut]
    timeline: list[TimelineStep]
    can_cancel: bool
    created_at: datetime
    customer: CustomerOut | None = None  # staff views only


class OrderSummary(Schema):
    id: int
    code: str
    fulfillment_type: FulfillmentType
    status: OrderStatus
    status_label: str
    store_name: str
    item_count: int
    grand_total: Money
    created_at: datetime
    pickup_slot_start: datetime | None
    preview: list[str]  # emojis of the first few items


class StatusUpdateIn(BaseModel):
    status: OrderStatus
    note: str | None = Field(default=None, max_length=200)


class CompleteIn(BaseModel):
    pin: str | None = Field(default=None, max_length=6)
