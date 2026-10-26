from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base, UTCDateTime, utcnow


def _enum(cls: type[StrEnum]) -> Enum:
    # Store enum *values* ("in_store") as plain strings so the DB stays portable.
    return Enum(cls, native_enum=False, length=32, values_callable=lambda e: [m.value for m in e])


class Role(StrEnum):
    CUSTOMER = "customer"
    STAFF = "staff"


class Fulfillment(StrEnum):
    DELIVERY = "delivery"
    PICKUP = "pickup"
    IN_STORE = "in_store"


class OrderStatus(StrEnum):
    PLACED = "placed"
    PACKED = "packed"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    READY_FOR_PICKUP = "ready_for_pickup"
    PICKED_UP = "picked_up"
    AWAITING_PAYMENT = "awaiting_payment"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentMethod(StrEnum):
    CASH = "cash"  # cash on delivery / pay at counter
    UPI = "upi"  # simulated online payment
    CARD = "card"  # simulated online payment


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(_enum(Role), default=Role.CUSTOMER)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    addresses: Mapped[list["Address"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class OtpCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(15), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    consumed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    label: Mapped[str] = mapped_column(String(30), default="Home")
    line1: Mapped[str] = mapped_column(String(255))
    line2: Mapped[str | None] = mapped_column(String(255))
    landmark: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100))
    pincode: Mapped[str] = mapped_column(String(10))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    user: Mapped[User] = relationship(back_populates="addresses")


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata")
    opens_at: Mapped[str] = mapped_column(String(5), default="07:00")  # local "HH:MM"
    closes_at: Mapped[str] = mapped_column(String(5), default="23:00")
    delivery_radius_km: Mapped[float] = mapped_column(Float, default=7.0)
    pickup_slot_minutes: Mapped[int] = mapped_column(Integer, default=30)
    pickup_slot_capacity: Mapped[int] = mapped_column(Integer, default=10)

    aisles: Mapped[list["Aisle"]] = relationship(
        back_populates="store", order_by="Aisle.number", cascade="all, delete-orphan"
    )


class Aisle(Base):
    __tablename__ = "aisles"
    __table_args__ = (UniqueConstraint("store_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(100))
    row_count: Mapped[int] = mapped_column(Integer, default=5)

    store: Mapped[Store] = relationship(back_populates="aisles")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    emoji: Mapped[str] = mapped_column(String(16), default="🛒")
    color: Mapped[str] = mapped_column(String(16), default="#f3f4f6")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    brand: Mapped[str | None] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(50))  # e.g. "500 ml", "1 kg", "6 pcs"
    description: Mapped[str | None] = mapped_column(Text)
    # All money is stored as integer paise (1 rupee = 100 paise) to avoid float rounding.
    mrp_paise: Mapped[int] = mapped_column(Integer)
    price_paise: Mapped[int] = mapped_column(Integer)
    emoji: Mapped[str] = mapped_column(String(16), default="🛒")
    image_url: Mapped[str | None] = mapped_column(String(500))
    # Comma-separated synonyms used by search, e.g. "dahi,yogurt" for curd.
    keywords: Mapped[str] = mapped_column(Text, default="")

    category: Mapped[Category] = relationship(back_populates="products")


class Inventory(Base):
    """Per-store stock level and the item's physical shelf location."""

    __tablename__ = "inventory"
    __table_args__ = (UniqueConstraint("store_id", "product_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    aisle_id: Mapped[int] = mapped_column(ForeignKey("aisles.id"))
    row_number: Mapped[int] = mapped_column(Integer)
    stock: Mapped[int] = mapped_column(Integer, default=0)

    store: Mapped[Store] = relationship()
    product: Mapped[Product] = relationship()
    aisle: Mapped[Aisle] = relationship()


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    fulfillment: Mapped[Fulfillment] = mapped_column(_enum(Fulfillment))
    status: Mapped[OrderStatus] = mapped_column(_enum(OrderStatus))

    # Delivery only
    address_id: Mapped[int | None] = mapped_column(ForeignKey("addresses.id"))
    delivery_address: Mapped[str | None] = mapped_column(Text)  # snapshot at order time
    eta_minutes: Mapped[int | None] = mapped_column(Integer)

    # Pickup only
    pickup_slot_start: Mapped[datetime | None] = mapped_column(UTCDateTime)
    pickup_slot_end: Mapped[datetime | None] = mapped_column(UTCDateTime)

    # Shown by the customer at the store: pickup OTP or in-store bill code.
    code: Mapped[str | None] = mapped_column(String(12), index=True)

    payment_method: Mapped[PaymentMethod] = mapped_column(_enum(PaymentMethod))
    payment_status: Mapped[PaymentStatus] = mapped_column(_enum(PaymentStatus), default=PaymentStatus.PENDING)

    item_total_paise: Mapped[int] = mapped_column(Integer)
    mrp_total_paise: Mapped[int] = mapped_column(Integer)
    delivery_fee_paise: Mapped[int] = mapped_column(Integer, default=0)
    handling_fee_paise: Mapped[int] = mapped_column(Integer, default=0)
    small_cart_fee_paise: Mapped[int] = mapped_column(Integer, default=0)
    total_paise: Mapped[int] = mapped_column(Integer)

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    store: Mapped[Store] = relationship()
    user: Mapped[User] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    events: Mapped[list["OrderEvent"]] = relationship(
        back_populates="order", order_by="OrderEvent.id", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    # Snapshots so old orders don't change when the catalog does.
    name: Mapped[str] = mapped_column(String(200))
    unit: Mapped[str] = mapped_column(String(50))
    emoji: Mapped[str] = mapped_column(String(16))
    price_paise: Mapped[int] = mapped_column(Integer)
    mrp_paise: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer)

    order: Mapped[Order] = relationship(back_populates="items")


class OrderEvent(Base):
    """Status history, used for the order-tracking timeline."""

    __tablename__ = "order_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(_enum(OrderStatus))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    order: Mapped[Order] = relationship(back_populates="events")
