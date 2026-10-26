"""Database bootstrap: create tables and load the demo catalog, stores and accounts."""

import logging
import random
import re
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.core.database import Base, SessionLocal, engine
from app.models import (
    Address,
    Category,
    Product,
    Store,
    StoreAisle,
    StoreInventory,
    User,
)
from app.seed.data import CATEGORIES, DEMO_CUSTOMER, SECTIONS, STAFF_USERS, STORES

logger = logging.getLogger("smartcart.seed")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _seed_catalog(db: Session) -> dict[str, list[Product]]:
    """Returns products grouped by top-level category slug, in shelf order."""
    by_top: dict[str, list[Product]] = {}
    for top_index, top in enumerate(CATEGORIES):
        parent = Category(
            name=top["name"],
            slug=top["slug"],
            emoji=top["emoji"],
            color=top["color"],
            sort_order=top_index,
        )
        db.add(parent)
        shelf: list[Product] = by_top.setdefault(top["slug"], [])
        for sub_index, sub in enumerate(top["children"]):
            child = Category(
                name=sub["name"],
                slug=sub["slug"],
                emoji=sub["emoji"],
                color=top["color"],
                sort_order=sub_index,
                parent=parent,
            )
            db.add(child)
            for row in sub["products"]:
                name, brand, unit, mrp, price, emoji, tags, popularity, *rest = row
                product = Product(
                    name=name,
                    slug=slugify(f"{name} {unit}"),
                    brand=brand,
                    description=top["about"].format(name=name, brand=brand or "", unit=unit).strip(),
                    unit_label=unit,
                    mrp=Decimal(mrp),
                    price=Decimal(price),
                    category=child,
                    emoji=emoji,
                    tags=[t.strip() for t in tags.split(",") if t.strip()],
                    is_veg=rest[0] if rest else True,
                    popularity=popularity,
                )
                db.add(product)
                shelf.append(product)
    db.flush()
    return by_top


def _seed_stores(db: Session, by_top: dict[str, list[Product]]) -> dict[str, Store]:
    stores: dict[str, Store] = {}
    for spec in STORES:
        store = Store(
            **{k: v for k, v in spec.items() if k not in ("aisle_order", "skip_ratio")},
        )
        db.add(store)
        db.flush()
        rng = random.Random(spec["slug"])  # deterministic demo stock
        for aisle_number, section_key in enumerate(spec["aisle_order"], start=1):
            aisle_name, top_slugs = SECTIONS[section_key]
            store.aisles.append(StoreAisle(number=aisle_number, name=aisle_name))
            products = [p for slug in top_slugs for p in by_top[slug]]
            carried = [p for p in products if p.popularity >= 60 or rng.random() >= spec["skip_ratio"]]
            rows = spec["layout_rows"]
            for index, product in enumerate(carried):
                out_of_stock = product.popularity < 90 and rng.random() < 0.06
                db.add(
                    StoreInventory(
                        store_id=store.id,
                        product_id=product.id,
                        stock=0 if out_of_stock else rng.randint(6, 40),
                        aisle=aisle_number,
                        row=1 + index * rows // len(carried),
                    )
                )
        stores[spec["slug"]] = store
    return stores


def _seed_users(db: Session, stores: dict[str, Store]) -> None:
    for spec in STAFF_USERS:
        store = stores.get(spec["store_slug"]) if spec["store_slug"] else None
        db.add(
            User(
                phone=spec["phone"],
                name=spec["name"],
                role=spec["role"],
                store_id=store.id if store else None,
            )
        )
    customer = User(phone=DEMO_CUSTOMER["phone"], name=DEMO_CUSTOMER["name"])
    customer.addresses.append(Address(**DEMO_CUSTOMER["address"], is_default=True))
    db.add(customer)


def seed_database(db: Session) -> None:
    by_top = _seed_catalog(db)
    stores = _seed_stores(db, by_top)
    _seed_users(db, stores)
    db.commit()
    products = db.scalar(select(func.count(Product.id)))
    logger.info("Seeded %s products across %s stores", products, len(stores))


def init_db(seed: bool = True, reset: bool = False) -> None:
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    if not seed:
        return
    with SessionLocal() as db:
        if db.scalar(select(func.count(Category.id))) == 0:
            seed_database(db)
