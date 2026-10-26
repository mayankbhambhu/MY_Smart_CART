from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import utcnow
from ..models import Fulfillment, Order, OrderStatus, Store
from ..schemas import PickupDay, PickupSlot
from .geo import hhmm_label, minutes_of_day, store_local_now

# Orders need some time to be packed before the first available slot.
PICKUP_LEAD_MINUTES = 30
PICKUP_DAYS_AHEAD = 2


def _booked_counts(db: Session, store: Store, start: datetime, end: datetime) -> dict[datetime, int]:
    rows = db.execute(
        select(Order.pickup_slot_start, func.count(Order.id))
        .where(
            Order.store_id == store.id,
            Order.fulfillment == Fulfillment.PICKUP,
            Order.status != OrderStatus.CANCELLED,
            Order.pickup_slot_start >= start,
            Order.pickup_slot_start < end,
        )
        .group_by(Order.pickup_slot_start)
    ).all()
    return {slot_start: count for slot_start, count in rows}


def pickup_slots(db: Session, store: Store, now: datetime | None = None) -> list[PickupDay]:
    now = now or utcnow()
    local_now = store_local_now(store, now)
    earliest = now + timedelta(minutes=PICKUP_LEAD_MINUTES)
    step = timedelta(minutes=store.pickup_slot_minutes)

    opens = minutes_of_day(store.opens_at)
    closes = minutes_of_day(store.closes_at)
    if closes <= opens:  # overnight store: offer pickups until midnight
        closes = 24 * 60

    midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    window_end = midnight + timedelta(days=PICKUP_DAYS_AHEAD)
    booked = _booked_counts(db, store, midnight, window_end)

    days: list[PickupDay] = []
    for offset in range(PICKUP_DAYS_AHEAD):
        day_start = midnight + timedelta(days=offset)
        slot_start = day_start + timedelta(minutes=opens)
        day_close = day_start + timedelta(minutes=closes)
        slots: list[PickupSlot] = []
        while slot_start + step <= day_close:
            if slot_start >= earliest:
                remaining = store.pickup_slot_capacity - booked.get(slot_start, 0)
                slots.append(
                    PickupSlot(
                        start=slot_start,
                        end=slot_start + step,
                        label=f"{hhmm_label(slot_start)} – {hhmm_label(slot_start + step)}",
                        remaining=max(0, remaining),
                        available=remaining > 0,
                    )
                )
            slot_start += step
        label = "Today" if offset == 0 else "Tomorrow" if offset == 1 else day_start.strftime("%a, %d %b")
        days.append(PickupDay(date=day_start.date(), label=label, slots=slots))
    return days


def validate_slot(db: Session, store: Store, start: datetime) -> tuple[datetime, datetime]:
    if start.tzinfo is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pickup slot must include a timezone")
    for day in pickup_slots(db, store):
        for slot in day.slots:
            if slot.start == start:
                if not slot.available:
                    raise HTTPException(status.HTTP_409_CONFLICT, "That pickup slot is full, please pick another")
                return slot.start, slot.end
    raise HTTPException(status.HTTP_400_BAD_REQUEST, "That pickup slot is not available")
