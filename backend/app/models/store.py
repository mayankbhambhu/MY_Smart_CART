from datetime import time

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.catalog import Product


class Store(Base):
    """A physical store. The same store serves delivery (as a dark store), scheduled pickup
    and walk-in shoppers, and has its own layout of aisles and rows."""

    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    address: Mapped[str] = mapped_column(String(240))
    city: Mapped[str] = mapped_column(String(60))
    pincode: Mapped[str] = mapped_column(String(10))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    phone: Mapped[str | None] = mapped_column(String(15))
    timezone: Mapped[str] = mapped_column(String(40), default="Asia/Kolkata")
    # Walk-in / delivery hours. opens_at == closes_at means open 24 hours; closes_at earlier than
    # opens_at means the store closes after midnight.
    opens_at: Mapped[time] = mapped_column(Time)
    closes_at: Mapped[time] = mapped_column(Time)
    # Hours the pickup counter is staffed (same day, start < end).
    pickup_start: Mapped[time] = mapped_column(Time)
    pickup_end: Mapped[time] = mapped_column(Time)

    supports_delivery: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_pickup: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_instore: Mapped[bool] = mapped_column(Boolean, default=True)
    delivery_radius_km: Mapped[float] = mapped_column(Float, default=5.0)

    pickup_slot_minutes: Mapped[int] = mapped_column(Integer, default=30)
    pickup_slot_capacity: Mapped[int] = mapped_column(Integer, default=8)

    # Number of rows (shelf bays) along each aisle; used to draw the in-store map.
    layout_rows: Mapped[int] = mapped_column(Integer, default=6)

    aisles: Mapped[list["StoreAisle"]] = relationship(
        back_populates="store", order_by="StoreAisle.number", cascade="all, delete-orphan"
    )


class StoreAisle(Base):
    __tablename__ = "store_aisles"
    __table_args__ = (UniqueConstraint("store_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(80))  # e.g. "Dairy & Bakery"

    store: Mapped[Store] = relationship(back_populates="aisles")


class StoreInventory(Base):
    """Stock and shelf location of one product in one store (Aisle 4 · Row 2)."""

    __tablename__ = "store_inventory"
    __table_args__ = (UniqueConstraint("store_id", "product_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    aisle: Mapped[int] = mapped_column(Integer)
    row: Mapped[int] = mapped_column(Integer)

    product: Mapped[Product] = relationship()
