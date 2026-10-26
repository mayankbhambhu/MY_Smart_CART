import math
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.core.types import utcnow
from app.models import Store
from app.schemas.store import AisleOut, StoreDetail, StoreOut


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def delivery_eta_minutes(distance_km: float) -> int:
    """Rough quick-commerce ETA: a few minutes to pack plus ride time."""
    return max(8, min(45, round(6 + distance_km * 3)))


def is_open(store: Store, at: datetime | None = None) -> bool:
    if store.opens_at == store.closes_at:
        return True  # 24 hours
    local = (at or utcnow()).astimezone(ZoneInfo(store.timezone)).time()
    if store.opens_at < store.closes_at:
        return store.opens_at <= local < store.closes_at
    return local >= store.opens_at or local < store.closes_at  # closes after midnight


def get_store(db: Session, store_id: int) -> Store:
    store = db.get(Store, store_id)
    if store is None:
        raise NotFound("Store")
    return store


def store_out(store: Store, lat: float | None = None, lng: float | None = None) -> StoreOut:
    out = StoreOut.model_validate(store)
    out.is_open_now = is_open(store)
    if lat is not None and lng is not None:
        distance = haversine_km(lat, lng, store.lat, store.lng)
        out.distance_km = round(distance, 2)
        out.delivers_here = store.supports_delivery and distance <= store.delivery_radius_km
        out.eta_minutes = delivery_eta_minutes(distance) if out.delivers_here else None
    return out


def store_detail(store: Store, lat: float | None = None, lng: float | None = None) -> StoreDetail:
    base = store_out(store, lat, lng)
    return StoreDetail(
        **base.model_dump(),
        layout_rows=store.layout_rows,
        aisles=[AisleOut.model_validate(a) for a in store.aisles],
    )


def stores_by_distance(db: Session, lat: float | None, lng: float | None) -> list[StoreOut]:
    stores = [store_out(s, lat, lng) for s in db.scalars(select(Store).order_by(Store.id))]
    if lat is not None and lng is not None:
        stores.sort(key=lambda s: s.distance_km or 0)
    return stores


def nearest_delivery_store(db: Session, lat: float, lng: float) -> StoreOut | None:
    for store in stores_by_distance(db, lat, lng):
        if store.delivers_here:
            return store
    return None
