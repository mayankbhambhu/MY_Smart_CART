"""Turns catalog rows into API objects enriched with one store's stock and shelf locations."""

from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFound
from app.models import Product, Store, StoreAisle, StoreInventory
from app.schemas.catalog import Availability, ProductOut, ShelfLocation


def location_label(aisle: int, row: int) -> str:
    return f"Aisle {aisle} · Row {row}"


@dataclass
class StoreContext:
    store_id: int
    inventory: dict[int, StoreInventory]
    aisle_names: dict[int, str]

    @classmethod
    def load(cls, db: Session, store_id: int, product_ids: Iterable[int] | None = None) -> "StoreContext":
        stmt = select(StoreInventory).where(StoreInventory.store_id == store_id)
        if product_ids is not None:
            stmt = stmt.where(StoreInventory.product_id.in_(set(product_ids)))
        inventory = {inv.product_id: inv for inv in db.scalars(stmt)}
        aisles = db.scalars(select(StoreAisle).where(StoreAisle.store_id == store_id))
        return cls(store_id, inventory, {a.number: a.name for a in aisles})

    def stock_of(self, product_id: int) -> int:
        inv = self.inventory.get(product_id)
        return inv.stock if inv else 0

    def location_of(self, product_id: int) -> ShelfLocation | None:
        inv = self.inventory.get(product_id)
        if inv is None:
            return None
        return ShelfLocation(
            aisle=inv.aisle,
            aisle_name=self.aisle_names.get(inv.aisle),
            row=inv.row,
            label=location_label(inv.aisle, inv.row),
        )


def load_store_context(db: Session, store_id: int | None, product_ids=None) -> StoreContext | None:
    if store_id is None:
        return None
    if db.get(Store, store_id) is None:
        raise NotFound("Store")
    return StoreContext.load(db, store_id, product_ids)


def product_out(product: Product, ctx: StoreContext | None) -> ProductOut:
    out = ProductOut.model_validate(product)
    if ctx is not None:
        stock = ctx.stock_of(product.id)
        out.availability = Availability(
            in_stock=stock > 0,
            stock=stock,
            max_qty=min(stock, get_settings().max_qty_per_item),
        )
        out.location = ctx.location_of(product.id)
    return out


def products_out(products: Iterable[Product], ctx: StoreContext | None) -> list[ProductOut]:
    """Serializes products, listing what's in stock first (then by popularity)."""
    items = [product_out(p, ctx) for p in products]
    if ctx is not None:
        items.sort(key=lambda p: not (p.availability and p.availability.in_stock))
    return items
