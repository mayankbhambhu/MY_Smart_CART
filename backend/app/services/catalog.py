from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..models import Inventory, Product
from ..schemas import ItemLocation, ProductOut


def location_of(inv: Inventory) -> ItemLocation:
    return ItemLocation(
        aisle_number=inv.aisle.number,
        aisle_name=inv.aisle.name,
        row_number=inv.row_number,
        label=f"Aisle {inv.aisle.number} · Row {inv.row_number}",
    )


def product_out(product: Product, inv: Inventory | None = None, include_location: bool = True) -> ProductOut:
    discount = 0
    if product.mrp_paise > product.price_paise > 0:
        discount = round((product.mrp_paise - product.price_paise) * 100 / product.mrp_paise)
    return ProductOut(
        id=product.id,
        category_id=product.category_id,
        name=product.name,
        brand=product.brand,
        unit=product.unit,
        description=product.description,
        mrp_paise=product.mrp_paise,
        price_paise=product.price_paise,
        discount_percent=discount,
        emoji=product.emoji,
        image_url=product.image_url,
        in_stock=inv is not None and inv.stock > 0,
        stock=inv.stock if inv is not None else 0,
        location=location_of(inv) if inv is not None and include_location else None,
    )


def store_inventory(
    db: Session, store_id: int, product_ids: Iterable[int] | None = None, lock: bool = False
) -> dict[int, Inventory]:
    """Inventory rows (with product and aisle loaded) for a store, keyed by product id."""
    stmt = (
        select(Inventory)
        .where(Inventory.store_id == store_id)
        .options(joinedload(Inventory.product), joinedload(Inventory.aisle))
    )
    if product_ids is not None:
        stmt = stmt.where(Inventory.product_id.in_(list(product_ids)))
    if lock:
        stmt = stmt.with_for_update(of=Inventory)
    return {inv.product_id: inv for inv in db.scalars(stmt)}
