from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.schemas.store import PickupDay, Serviceability, StoreDetail, StoreOut
from app.services.slots import pickup_days
from app.services.stores import get_store, nearest_delivery_store, store_detail, stores_by_distance

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("", response_model=list[StoreOut])
def list_stores(db: DbSession, lat: float | None = None, lng: float | None = None):
    return stores_by_distance(db, lat, lng)


@router.get("/serviceability", response_model=Serviceability)
def serviceability(db: DbSession, lat: float = Query(ge=-90, le=90), lng: float = Query(ge=-180, le=180)):
    store = nearest_delivery_store(db, lat, lng)
    if store is None:
        return Serviceability(
            deliverable=False,
            store=None,
            eta_minutes=None,
            message="We don't deliver here yet. You can still schedule a pickup or shop in store.",
        )
    return Serviceability(
        deliverable=True,
        store=store,
        eta_minutes=store.eta_minutes,
        message=f"Delivery in {store.eta_minutes} minutes",
    )


@router.get("/{store_id}", response_model=StoreDetail)
def get_store_detail(store_id: int, db: DbSession, lat: float | None = None, lng: float | None = None):
    return store_detail(get_store(db, store_id), lat, lng)


@router.get("/{store_id}/pickup-slots", response_model=list[PickupDay])
def list_pickup_slots(store_id: int, db: DbSession, days: int = Query(default=3, ge=1, le=7)):
    store = get_store(db, store_id)
    if not store.supports_pickup:
        return []
    return pickup_days(db, store, days=days)
