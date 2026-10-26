from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from .models import Fulfillment, OrderStatus, PaymentMethod, PaymentStatus, Role


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _normalize_phone(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) != 10 or digits[0] not in "6789":
        raise ValueError("Enter a valid 10-digit mobile number")
    return digits


Phone = Annotated[str, AfterValidator(_normalize_phone)]


# ---------- Auth & users ----------


class OtpRequest(BaseModel):
    phone: Phone


class OtpRequestResponse(BaseModel):
    message: str
    expires_in_seconds: int
    dev_otp: str | None = Field(None, description="Only returned when the server runs in dev mode")


class OtpVerify(BaseModel):
    phone: Phone
    otp: str = Field(min_length=4, max_length=8)


class UserOut(ORMModel):
    id: int
    phone: str
    name: str | None
    email: str | None
    role: Role


class UserUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    email: str | None = Field(None, max_length=255)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Addresses ----------


class AddressIn(BaseModel):
    label: str = Field("Home", max_length=30)
    line1: str = Field(min_length=3, max_length=255)
    line2: str | None = Field(None, max_length=255)
    landmark: str | None = Field(None, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    pincode: str = Field(pattern=r"^\d{6}$")
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class AddressOut(ORMModel):
    id: int
    label: str
    line1: str
    line2: str | None
    landmark: str | None
    city: str
    pincode: str
    lat: float
    lng: float


# ---------- Stores ----------


class AisleOut(ORMModel):
    number: int
    name: str
    row_count: int


class StoreOut(ORMModel):
    id: int
    name: str
    address: str
    city: str
    lat: float
    lng: float
    opens_at: str
    closes_at: str
    is_open: bool = False
    distance_km: float | None = None
    delivers_here: bool | None = None
    delivery_eta_minutes: int | None = None


class StoreLayoutOut(StoreOut):
    aisles: list[AisleOut]


class StoreBrief(ORMModel):
    id: int
    name: str
    address: str


class PickupSlot(BaseModel):
    start: datetime
    end: datetime
    label: str
    remaining: int
    available: bool


class PickupDay(BaseModel):
    date: date
    label: str
    slots: list[PickupSlot]


class PickupSlotsResponse(BaseModel):
    store_id: int
    days: list[PickupDay]


# ---------- Catalog ----------


class CategoryOut(ORMModel):
    id: int
    name: str
    slug: str
    emoji: str
    color: str


class ItemLocation(BaseModel):
    aisle_number: int
    aisle_name: str
    row_number: int
    label: str  # "Aisle 4 · Row 2"


class ProductOut(ORMModel):
    id: int
    category_id: int
    name: str
    brand: str | None
    unit: str
    description: str | None
    mrp_paise: int
    price_paise: int
    discount_percent: int
    emoji: str
    image_url: str | None
    in_stock: bool = True
    stock: int | None = None
    location: ItemLocation | None = None


class CategoryWithProducts(CategoryOut):
    products: list[ProductOut]


# ---------- Cart & bill ----------


class CartItemIn(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=50)


class QuoteRequest(BaseModel):
    store_id: int
    fulfillment: Fulfillment = Fulfillment.DELIVERY
    items: list[CartItemIn] = Field(max_length=100)


class Bill(BaseModel):
    item_total_paise: int
    mrp_total_paise: int
    savings_paise: int
    delivery_fee_paise: int
    handling_fee_paise: int
    small_cart_fee_paise: int
    total_paise: int
    free_delivery_threshold_paise: int | None = None
    amount_to_free_delivery_paise: int | None = None


class QuoteLine(BaseModel):
    product: ProductOut
    quantity: int
    available_quantity: int
    line_total_paise: int
    line_mrp_paise: int


class QuoteResponse(BaseModel):
    store_id: int
    fulfillment: Fulfillment
    lines: list[QuoteLine]
    bill: Bill
    issues: list[str]
    can_checkout: bool


# ---------- In-store shopping ----------


class InStoreMatchRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000, description="Free-form list, typed or spoken")


class InStoreMatch(BaseModel):
    query: str
    quantity: int
    product: ProductOut
    alternatives: list[ProductOut]


class InStoreMatchResponse(BaseModel):
    matches: list[InStoreMatch]
    unmatched: list[str]


class InStoreListRequest(BaseModel):
    items: list[CartItemIn] = Field(max_length=100)


class InStoreLine(BaseModel):
    product: ProductOut
    quantity: int
    # How many of `quantity` can actually be bought; only these count towards the bill.
    available_quantity: int
    line_total_paise: int
    line_mrp_paise: int


class InStoreListResponse(BaseModel):
    store: StoreLayoutOut
    # Sorted in walking order: aisle by aisle, row by row.
    lines: list[InStoreLine]
    bill: Bill
    issues: list[str]


# ---------- Orders ----------


class OrderCreate(BaseModel):
    store_id: int
    fulfillment: Fulfillment
    items: list[CartItemIn] = Field(min_length=1, max_length=100)
    payment_method: PaymentMethod = PaymentMethod.CASH
    address_id: int | None = None
    pickup_slot_start: datetime | None = None
    notes: str | None = Field(None, max_length=500)


class OrderItemOut(ORMModel):
    product_id: int
    name: str
    unit: str
    emoji: str
    price_paise: int
    mrp_paise: int
    quantity: int
    location: ItemLocation | None = None


class OrderEventOut(BaseModel):
    status: OrderStatus
    label: str
    created_at: datetime


class OrderStep(BaseModel):
    status: OrderStatus
    label: str
    done: bool
    at: datetime | None


class OrderOut(BaseModel):
    id: int
    store: StoreBrief
    fulfillment: Fulfillment
    status: OrderStatus
    status_label: str
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    delivery_address: str | None
    eta_minutes: int | None
    pickup_slot_start: datetime | None
    pickup_slot_end: datetime | None
    code: str | None
    notes: str | None
    bill: Bill
    items: list[OrderItemOut]
    steps: list[OrderStep]
    can_cancel: bool
    created_at: datetime


class StaffOrderOut(OrderOut):
    customer_phone: str
    customer_name: str | None
    next_status: OrderStatus | None
    next_status_label: str | None


class VerifyCodeRequest(BaseModel):
    store_id: int
    code: str = Field(min_length=4, max_length=12)
