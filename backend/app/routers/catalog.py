from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Category, Product, Store
from ..schemas import CategoryOut, CategoryWithProducts, ProductOut
from ..services.catalog import product_out, store_inventory
from ..services.search import rank_products

router = APIRouter(tags=["catalog"])


def _require_store(db: Session, store_id: int) -> Store:
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Store not found")
    return store


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.sort_order, Category.name)).all()


@router.get("/home", response_model=list[CategoryWithProducts])
def home_feed(store_id: int, per_category: int = Query(12, ge=1, le=50), db: Session = Depends(get_db)):
    """Category rails for the home screen."""
    _require_store(db, store_id)
    inventory = store_inventory(db, store_id)
    rails = []
    for category in db.scalars(select(Category).order_by(Category.sort_order, Category.name)):
        stocked = [inv for inv in inventory.values() if inv.product.category_id == category.id]
        # In-stock first, then the biggest discounts.
        stocked.sort(key=lambda inv: (inv.stock <= 0, inv.product.price_paise - inv.product.mrp_paise, inv.product.id))
        if not stocked:
            continue
        rails.append(
            CategoryWithProducts(
                **CategoryOut.model_validate(category).model_dump(),
                products=[product_out(inv.product, inv) for inv in stocked[:per_category]],
            )
        )
    return rails


@router.get("/products", response_model=list[ProductOut])
def list_products(
    store_id: int,
    category_id: int | None = None,
    q: str | None = Query(None, max_length=100),
    limit: int = Query(60, ge=1, le=200),
    db: Session = Depends(get_db),
):
    _require_store(db, store_id)
    inventory = store_inventory(db, store_id)
    products = [inv.product for inv in inventory.values()]
    if category_id is not None:
        products = [p for p in products if p.category_id == category_id]

    if q and q.strip():
        in_stock = {pid for pid, inv in inventory.items() if inv.stock > 0}
        products = [p for p, _ in rank_products(products, q, in_stock=in_stock, limit=limit)]
    else:
        products.sort(key=lambda p: (inventory[p.id].stock <= 0, p.name))
        products = products[:limit]
    return [product_out(p, inventory[p.id]) for p in products]


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, store_id: int, db: Session = Depends(get_db)):
    _require_store(db, store_id)
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    inv = store_inventory(db, store_id, [product_id]).get(product_id)
    return product_out(product, inv)
