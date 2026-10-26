from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession
from app.core.errors import NotFound
from app.models import Category, Product
from app.schemas.catalog import (
    CategoryOut,
    CategoryPage,
    CategoryTree,
    HomeFeed,
    HomeSection,
    ProductDetail,
    SearchResult,
)
from app.services.catalog import load_store_context, product_out, products_out
from app.services.instore import subcategory_names
from app.services.matching import ProductMatcher, parse_size, words_of

router = APIRouter(tags=["catalog"])

SEARCH_THRESHOLD = 55


def _top_categories(db: DbSession) -> list[Category]:
    return list(
        db.scalars(
            select(Category)
            .where(Category.parent_id.is_(None))
            .order_by(Category.sort_order)
            .options(selectinload(Category.children))
        )
    )


def _active_products_in(db: DbSession, category_ids: list[int]) -> list[Product]:
    return list(
        db.scalars(
            select(Product)
            .where(Product.category_id.in_(category_ids), Product.is_active.is_(True))
            .order_by(Product.popularity.desc(), Product.id)
        )
    )


@router.get("/categories", response_model=list[CategoryTree])
def list_categories(db: DbSession):
    return _top_categories(db)


@router.get("/home", response_model=HomeFeed)
def home_feed(db: DbSession, store_id: int | None = None):
    categories = _top_categories(db)
    ctx = load_store_context(db, store_id)
    sections = []
    for category in categories[:8]:
        products = _active_products_in(db, [c.id for c in category.children])[:12]
        if products:
            sections.append(
                HomeSection(
                    title=category.name,
                    category_slug=category.slug,
                    products=products_out(products, ctx),
                )
            )
    return HomeFeed(categories=categories, sections=sections)


@router.get("/categories/{slug}", response_model=CategoryPage)
def category_page(slug: str, db: DbSession, store_id: int | None = None, sub: str | None = None):
    category = db.scalars(select(Category).where(Category.slug == slug)).first()
    if category is None:
        raise NotFound("Category")
    if category.parent_id is not None:  # a subcategory link: open its parent with it selected
        sub, category = category.slug, category.parent

    subcategories = list(category.children)
    selected = [c for c in subcategories if c.slug == sub] if sub else subcategories
    if sub and not selected:
        raise NotFound("Category")
    ctx = load_store_context(db, store_id)
    products = _active_products_in(db, [c.id for c in selected])
    return CategoryPage(
        category=CategoryOut.model_validate(category),
        subcategories=[CategoryOut.model_validate(c) for c in subcategories],
        active_subcategory=sub,
        products=products_out(products, ctx),
    )


@router.get("/products/{product_id}", response_model=ProductDetail)
def product_detail(product_id: int, db: DbSession, store_id: int | None = None):
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise NotFound("Product")
    similar = [p for p in _active_products_in(db, [product.category_id]) if p.id != product.id][:10]
    ctx = load_store_context(db, store_id, [product.id, *(p.id for p in similar)])
    base = product_out(product, ctx)
    parent = product.category.parent
    return ProductDetail(
        **base.model_dump(),
        description=product.description,
        tags=product.tags or [],
        category=CategoryOut.model_validate(product.category),
        parent_category=CategoryOut.model_validate(parent) if parent else None,
        similar=products_out(similar, ctx),
    )


@router.get("/search", response_model=SearchResult)
def search(
    db: DbSession,
    q: str = Query(min_length=1, max_length=80),
    store_id: int | None = None,
    limit: int = Query(default=40, ge=1, le=100),
):
    products = list(db.scalars(select(Product).where(Product.is_active.is_(True))))
    matcher = ProductMatcher(products, subcategory_names(db))
    matches = [m for m in matcher.search(words_of(q), parse_size(q)) if m.score >= SEARCH_THRESHOLD]
    found = [m.product for m in matches[:limit]]
    ctx = load_store_context(db, store_id, [p.id for p in found])
    return SearchResult(query=q, products=products_out(found, ctx))
