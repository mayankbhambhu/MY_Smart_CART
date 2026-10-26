import math
from datetime import datetime, time
from zoneinfo import ZoneInfo

from ..database import utcnow
from ..models import Store

# Rough quick-commerce ETA model: fixed packing time plus rider travel time.
PACKING_MINUTES = 4
RIDER_MINUTES_PER_KM = 2.5


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def delivery_eta_minutes(distance_km: float) -> int:
    return max(8, round(PACKING_MINUTES + distance_km * RIDER_MINUTES_PER_KM))


def minutes_of_day(value: str) -> int:
    """'07:30' -> 450. '24:00' is allowed and means end of day."""
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def store_local_now(store: Store, now: datetime | None = None) -> datetime:
    return (now or utcnow()).astimezone(ZoneInfo(store.timezone))


def is_store_open(store: Store, now: datetime | None = None) -> bool:
    local = store_local_now(store, now)
    current = local.hour * 60 + local.minute
    opens, closes = minutes_of_day(store.opens_at), minutes_of_day(store.closes_at)
    if opens <= closes:
        return opens <= current < closes
    # Overnight hours, e.g. 06:00 -> 02:00
    return current >= opens or current < closes


def hhmm_label(t: time | datetime) -> str:
    return t.strftime("%I:%M %p").lstrip("0")
