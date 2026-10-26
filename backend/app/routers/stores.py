from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Fulfillment, Store
from ..schemas import (
    AisleOut,
    InStoreLine,
    InStoreListRequest,
    InStoreListResponse,
    InStoreMatch,
    InStoreMatchRequest,
    InStoreMatchResponse,
    PickupSlotsResponse,
    StoreLayoutOut,
    StoreOut,
)
from ..services.catalog import product_out, store_inventory
from ..services.geo import delivery_eta_minutes, haversine_km, is_store_open
from ..services.orders import resolve_lines, totals
from ..services.pricing import compute_bill
from ..services.search import parse_shopping_list, rank_products
from ..services.slots import pickup_slots

router = APIRouter(prefix="/stores", tags=["stores"])


def _store_out(store: Store, lat: float | None = None, lng: float | None = None) -> StoreOut:
    out = StoreOut.model_validate(store)
    out.is_open = is_store_open(store)
    if lat is not None and lng is not None:
        distance = haversine_km(lat, lng, store.lat, store.lng)
        out.distance_km = round(distance, 2)
        out.delivers_here = distance <= store.delivery_radius_km
        out.delivery_eta_minutes = delivery_eta_minutes(distance) if out.delivers_here else None
    return out


def _layout(store: Store) -> StoreLayoutOut:
    return StoreLayoutOut(
        **_store_out(store).model_dump(),
        aisles=[AisleOut.model_validate(a) for a in store.aisles],
    )


def _get_store(db: Session, store_id: int) -> Store:
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Store not found")
    return store


@router.get("", response_model=list[StoreOut])
def list_stores(
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    db: Session = Depends(get_db),
):
    stores = [_store_out(s, lat, lng) for s in db.scalars(select(Store))]
    stores.sort(key=lambda s: (s.distance_km is None, s.distance_km or 0, s.id))
    return stores


@router.get("/nearest", response_model=StoreOut)
def nearest_store(
    lat: float = Query(ge=-90, le=90), lng: float = Query(ge=-180, le=180), db: Session = Depends(get_db)
):
    """The store that should serve home delivery for this location."""
    candidates = [s for s in list_stores(lat, lng, db) if s.delivers_here]
    if not candidates:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sorry, we don't deliver to this location yet")
    # Prefer an open store; among those, the closest one.
    candidates.sort(key=lambda s: (not s.is_open, s.distance_km))
    return candidates[0]


@router.get("/{store_id}", response_model=StoreLayoutOut)
def get_store(store_id: int, db: Session = Depends(get_db)):
    return _layout(_get_store(db, store_id))


@router.get("/{store_id}/pickup-slots", response_model=PickupSlotsResponse)
def get_pickup_slots(store_id: int, db: Session = Depends(get_db)):
    store = _get_store(db, store_id)
    return PickupSlotsResponse(store_id=store.id, days=pickup_slots(db, store))


@router.post("/{store_id}/instore/match", response_model=InStoreMatchResponse)
def match_shopping_list(store_id: int, body: InStoreMatchRequest, db: Session = Depends(get_db)):
    """Turn a typed or spoken list ("2 milk, bread and eggs") into products with shelf locations."""
    _get_store(db, store_id)
    inventory = store_inventory(db, store_id)
    products = [inv.product for inv in inventory.values()]
    in_stock = {pid for pid, inv in inventory.items() if inv.stock > 0}

    matches: list[InStoreMatch] = []
    unmatched: list[str] = []
    for item in parse_shopping_list(body.text):
        ranked = rank_products(products, item.query, in_stock=in_stock, limit=5)
        if not ranked:
            unmatched.append(item.query)
            continue
        top_score = max(s for _, s in ranked)
        # Only offer alternatives that are nearly as good a match ("milk" -> other milks, not dals).
        close = [p for p, s in ranked if s >= top_score * 0.6]
        best, *others = [product_out(p, inventory[p.id]) for p in close]
        matches.append(InStoreMatch(query=item.query, quantity=item.quantity, product=best, alternatives=others))
    return InStoreMatchResponse(matches=matches, unmatched=unmatched)


@router.post("/{store_id}/instore/list", response_model=InStoreListResponse)
def shopping_route(store_id: int, body: InStoreListRequest, db: Session = Depends(get_db)):
    """Locations for every item on the list, in walking order, plus the running total."""
    store = _get_store(db, store_id)
    lines, issues = resolve_lines(db, store.id, body.items)
    lines.sort(key=lambda line: (line.inventory.aisle.number, line.inventory.row_number, line.inventory.product.name))
    item_total, mrp_total = totals(lines)
    return InStoreListResponse(
        store=_layout(store),
        lines=[
            InStoreLine(
                product=product_out(line.inventory.product, line.inventory),
                quantity=line.quantity,
                line_total_paise=line.inventory.product.price_paise * line.quantity,
                line_mrp_paise=line.inventory.product.mrp_paise * line.quantity,
            )
            for line in lines
        ],
        bill=compute_bill(Fulfillment.IN_STORE, item_total, mrp_total),
        issues=issues,
    )
