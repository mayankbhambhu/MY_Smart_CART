"""In-store shopping: turn what the shopper says they want into shelf locations and a total."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.types import to_money
from app.models import Category, Product, Store
from app.schemas.instore import (
    AisleStop,
    ResolvedItem,
    ShoppingListIn,
    ShoppingListOut,
    UnmatchedItem,
)
from app.services.catalog import StoreContext, product_out
from app.services.matching import (
    MATCH_THRESHOLD,
    SUGGESTION_THRESHOLD,
    ListLine,
    Match,
    ProductMatcher,
    packs_for_pieces,
    parse_chunk,
    walking_route,
    words_of,
)
from app.services.stores import store_out


def subcategory_names(db: Session) -> dict[int, str]:
    return {c.id: c.name for c in db.scalars(select(Category).where(Category.parent_id.is_not(None)))}


def store_matcher(db: Session, ctx: StoreContext) -> tuple[ProductMatcher, dict[int, Product]]:
    products = list(
        db.scalars(select(Product).where(Product.id.in_(ctx.inventory), Product.is_active.is_(True)))
    )
    return ProductMatcher(products, subcategory_names(db)), {p.id: p for p in products}


@dataclass
class _Picked:
    query: str
    quantity: int
    product: Product
    confidence: int
    alternatives: list[Product]


def resolve_shopping_list(db: Session, store: Store, body: ShoppingListIn) -> ShoppingListOut:
    ctx = StoreContext.load(db, store.id)
    matcher, by_id = store_matcher(db, ctx)
    in_stock = {pid: inv.stock > 0 for pid, inv in ctx.inventory.items()}

    lines: list[ListLine] = []
    for item in body.items:
        requests = parse_chunk(item.query)
        words = requests[0].words if requests else words_of(item.query)
        size = requests[0].size if requests else None
        matches = matcher.search(words, size, in_stock)
        pinned = by_id.get(item.product_id) if item.product_id else None
        if pinned is not None:
            matches = [Match(pinned, 100.0), *(m for m in matches if m.product.id != pinned.id)]
        lines.append(ListLine(query=item.query.strip(), quantity=item.quantity, matches=matches))
    if body.text:
        lines.extend(matcher.parse_list(body.text, in_stock))

    picked: dict[int, _Picked] = {}
    unmatched: list[UnmatchedItem] = []
    for line in lines:
        best = line.best
        if best is None:
            suggestions = [m.product for m in line.matches if m.score >= SUGGESTION_THRESHOLD][:3]
            unmatched.append(
                UnmatchedItem(
                    query=line.query,
                    quantity=line.quantity,
                    suggestions=[product_out(p, ctx) for p in suggestions],
                )
            )
            continue
        product = best.product
        quantity = line.quantity
        if line.pieces:
            quantity = packs_for_pieces(line.pieces, product.unit_label) or quantity
        if product.id in picked:
            picked[product.id].quantity += quantity
            continue
        alternatives = [
            m.product
            for m in line.matches[1:]
            if m.score >= MATCH_THRESHOLD - 7 and m.product.id != product.id
        ][:4]
        picked[product.id] = _Picked(
            query=line.query,
            quantity=quantity,
            product=product,
            confidence=min(100, round(best.score)),
            alternatives=alternatives,
        )

    entries = list(picked.values())
    spots = [(ctx.inventory[e.product.id].aisle, ctx.inventory[e.product.id].row) for e in entries]
    ordered = [entries[i] for i in walking_route(spots)]
    items: list[ResolvedItem] = []
    total = mrp_total = Decimal(0)
    item_count = out_of_stock = 0
    stops: dict[int, AisleStop] = {}
    for step, entry in enumerate(ordered, start=1):
        product = entry.product
        available = in_stock.get(product.id, False)
        line_total = product.price * entry.quantity
        if available:
            total += line_total
            mrp_total += product.mrp * entry.quantity
            item_count += entry.quantity
        else:
            out_of_stock += 1
        aisle = ctx.inventory[product.id].aisle
        stop = stops.setdefault(aisle, AisleStop(aisle=aisle, name=ctx.aisle_names.get(aisle), item_count=0))
        stop.item_count += 1
        items.append(
            ResolvedItem(
                query=entry.query,
                quantity=entry.quantity,
                product=product_out(product, ctx),
                in_stock=available,
                line_total=to_money(line_total),
                confidence=entry.confidence,
                step=step,
                alternatives=[product_out(p, ctx) for p in entry.alternatives],
            )
        )

    return ShoppingListOut(
        store=store_out(store),
        layout_rows=store.layout_rows,
        aisle_count=len(store.aisles),
        items=items,
        unmatched=unmatched,
        route=list(stops.values()),
        item_count=item_count,
        total=to_money(total),
        mrp_total=to_money(mrp_total),
        savings=to_money(mrp_total - total),
        out_of_stock_count=out_of_stock,
    )
