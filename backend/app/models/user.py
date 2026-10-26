from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import ExactString, UTCDateTime, utcnow
from app.models.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(80))
    email: Mapped[str | None] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), default=UserRole.CUSTOMER)
    # Staff accounts belong to one store; customers leave this empty.
    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    addresses: Mapped[list["Address"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="Address.id"
    )

    @property
    def is_staff(self) -> bool:
        return self.role in (UserRole.STAFF, UserRole.ADMIN)


class OtpRequest(Base):
    __tablename__ = "otp_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(15), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    # Set when the SMS provider generated the code and checks it itself (Message Central).
    provider_ref: Mapped[str | None] = mapped_column(ExactString(100))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    consumed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(20), default="Home")  # Home / Work / Other
    receiver_name: Mapped[str] = mapped_column(String(80))
    receiver_phone: Mapped[str | None] = mapped_column(String(15))
    house: Mapped[str] = mapped_column(String(120))  # flat / house no. / floor / building
    area: Mapped[str] = mapped_column(String(160))  # street / locality
    landmark: Mapped[str | None] = mapped_column(String(120))
    city: Mapped[str] = mapped_column(String(60))
    pincode: Mapped[str] = mapped_column(String(10))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    user: Mapped[User] = relationship(back_populates="addresses")

    def one_line(self) -> str:
        parts = [self.house, self.area, self.landmark, f"{self.city} {self.pincode}"]
        return ", ".join(p for p in parts if p)
