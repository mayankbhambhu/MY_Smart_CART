from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import ExactString, Money, UTCDateTime, utcnow
from app.models.enums import PaymentState

if TYPE_CHECKING:
    from app.models.order import Order


class Payment(Base):
    """One online payment for an order: a Razorpay order the customer pays (possibly after a few
    failed attempts), plus what happened to the money afterwards."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20))  # razorpay | simulated
    provider_order_id: Mapped[str] = mapped_column(ExactString(64), unique=True, index=True)
    provider_payment_id: Mapped[str | None] = mapped_column(ExactString(64), index=True)
    amount: Mapped[Decimal] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[str] = mapped_column(String(20), default=PaymentState.CREATED)
    method: Mapped[str | None] = mapped_column(String(30))  # upi, card, netbanking, wallet...
    error: Mapped[str | None] = mapped_column(String(300))
    refund_id: Mapped[str | None] = mapped_column(ExactString(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    order: Mapped["Order"] = relationship(back_populates="payments")
