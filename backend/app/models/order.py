from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import Money, UTCDateTime, utcnow
from app.models.enums import OrderStatus, PaymentStatus
from app.models.store import Store
from app.models.user import User

if TYPE_CHECKING:
    from app.models.payment import Payment


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)  # shown to customers
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    fulfillment_type: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(30), default=OrderStatus.PLACED, index=True)
    payment_method: Mapped[str] = mapped_column(String(20))
    payment_status: Mapped[str] = mapped_column(String(20), default=PaymentStatus.PENDING)

    # Delivery: snapshot of the address at order time, so later edits don't rewrite history.
    delivery_address: Mapped[dict | None] = mapped_column(JSON)
    eta_minutes: Mapped[int | None] = mapped_column(Integer)

    # Scheduled pickup window.
    pickup_slot_start: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)
    pickup_slot_end: Mapped[datetime | None] = mapped_column(UTCDateTime)
    # PIN the customer shows at the counter so staff can hand over a pickup order.
    handover_pin: Mapped[str | None] = mapped_column(String(6))

    item_total: Mapped[Decimal] = mapped_column(Money)
    mrp_total: Mapped[Decimal] = mapped_column(Money)
    delivery_fee: Mapped[Decimal] = mapped_column(Money, default=Decimal(0))
    handling_fee: Mapped[Decimal] = mapped_column(Money, default=Decimal(0))
    small_cart_fee: Mapped[Decimal] = mapped_column(Money, default=Decimal(0))
    grand_total: Mapped[Decimal] = mapped_column(Money)

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    store: Mapped[Store] = relationship()
    user: Mapped[User] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id"
    )
    events: Mapped[list["OrderStatusEvent"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderStatusEvent.id"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="Payment.id"
    )

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def latest_payment(self) -> "Payment | None":
        return self.payments[-1] if self.payments else None


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    # Snapshots so the receipt never changes when the catalog does.
    name: Mapped[str] = mapped_column(String(160))
    unit_label: Mapped[str] = mapped_column(String(40))
    emoji: Mapped[str] = mapped_column(String(16))
    image_url: Mapped[str | None] = mapped_column(String(300))
    price: Mapped[Decimal] = mapped_column(Money)
    mrp: Mapped[Decimal] = mapped_column(Money)
    quantity: Mapped[int] = mapped_column(Integer)
    line_total: Mapped[Decimal] = mapped_column(Money)
    # Shelf location in the fulfilling store (picking list for staff, map for in-store shoppers).
    aisle: Mapped[int | None] = mapped_column(Integer)
    row: Mapped[int | None] = mapped_column(Integer)

    order: Mapped[Order] = relationship(back_populates="items")


class OrderStatusEvent(Base):
    __tablename__ = "order_status_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30))
    note: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    order: Mapped[Order] = relationship(back_populates="events")
