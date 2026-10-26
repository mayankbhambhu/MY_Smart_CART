from datetime import date, datetime, time

from app.schemas.common import Schema


class AisleOut(Schema):
    number: int
    name: str


class StoreOut(Schema):
    id: int
    name: str
    slug: str
    address: str
    city: str
    pincode: str
    lat: float
    lng: float
    phone: str | None
    timezone: str
    opens_at: time
    closes_at: time
    pickup_start: time
    pickup_end: time
    supports_delivery: bool
    supports_pickup: bool
    supports_instore: bool
    delivery_radius_km: float
    is_open_now: bool = False
    # Present when the request includes the shopper's lat/lng.
    distance_km: float | None = None
    delivers_here: bool | None = None
    eta_minutes: int | None = None


class StoreDetail(StoreOut):
    layout_rows: int
    aisles: list[AisleOut]


class Serviceability(Schema):
    deliverable: bool
    store: StoreOut | None
    eta_minutes: int | None
    message: str


class PickupSlot(Schema):
    start: datetime
    end: datetime
    label: str
    available: bool
    remaining: int


class PickupDay(Schema):
    date: date
    label: str
    slots: list[PickupSlot]
