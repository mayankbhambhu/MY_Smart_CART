from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import Money, UTCDateTime, utcnow


class Category(Base):
    """Two levels, like Blinkit/Zepto: top-level groups (e.g. "Dairy, Bread & Eggs") shown on the
    home grid, and subcategories (e.g. "Milk") shown in the category page sidebar."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)
    emoji: Mapped[str] = mapped_column(String(16), default="🛒")
    image_url: Mapped[str | None] = mapped_column(String(300))
    color: Mapped[str] = mapped_column(String(9), default="#EEF6F0")  # tile background
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    parent: Mapped["Category | None"] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list["Category"]] = relationship(back_populates="parent", order_by="Category.sort_order")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    brand: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    unit_label: Mapped[str] = mapped_column(String(40))  # "500 ml", "1 kg", "6 pcs"
    mrp: Mapped[Decimal] = mapped_column(Money)
    price: Mapped[Decimal] = mapped_column(Money)
    # Always a subcategory (second level).
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    emoji: Mapped[str] = mapped_column(String(16), default="🛒")
    image_url: Mapped[str | None] = mapped_column(String(300))
    # Extra search words: synonyms, Hindi names, common misspellings ("doodh", "dahi", "maggie").
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_veg: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    popularity: Mapped[int] = mapped_column(Integer, default=0)  # higher sorts first
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    category: Mapped[Category] = relationship()

    @property
    def discount_percent(self) -> int:
        if not self.mrp or self.mrp <= self.price:
            return 0
        return int((self.mrp - self.price) * 100 / self.mrp)
