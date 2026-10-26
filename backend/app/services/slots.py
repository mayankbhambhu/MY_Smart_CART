"""Pickup slot generation and validation for scheduled pickup orders."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.types import utcnow
from app.models import FulfillmentType, Order, OrderStatus, Store
from app.schemas.store import PickupDay, PickupSlot


def _clock(dt: datetime) -> str:
    return dt.strftime("%I:%M %p").lstrip("0")


def slot_label(start: datetime, end: datetime) -> str:
    return f"{_clock(start)} – {_clock(end)}"


def day_label(day: date, today: date) -> str:
    if day == today:
        return "Today"
    if day == today + timedelta(days=1):
        return "Tomorrow"
    return day.strftime("%a, %d %b")


def booked_counts(db: Session, store_id: int, start: datetime, end: datetime) -> dict[datetime, int]:
    rows = db.execute(
        select(Order.pickup_slot_start, func.count(Order.id))
        .where(
            Order.store_id == store_id,
            Order.fulfillment_type == FulfillmentType.PICKUP,
            Order.status != OrderStatus.CANCELLED,
            Order.pickup_slot_start >= start,
            Order.pickup_slot_start < end,
        )
        .group_by(Order.pickup_slot_start)
    )
    return {slot_start: count for slot_start, count in rows}


def pickup_days(
    db: Session, store: Store, now: datetime | None = None, days: int | None = None
) -> list[PickupDay]:
    settings = get_settings()
    now = now or utcnow()
    days = days or settings.pickup_days_ahead
    tz = ZoneInfo(store.timezone)
    today = now.astimezone(tz).date()
    earliest = now + timedelta(minutes=settings.pickup_lead_minutes)
    slot_length = timedelta(minutes=store.pickup_slot_minutes)

    window_start = datetime.combine(today, time(0), tz)
    window_end = window_start + timedelta(days=days)
    booked = booked_counts(db, store.id, window_start, window_end)

    result: list[PickupDay] = []
    for offset in range(days):
        day = today + timedelta(days=offset)
        start = datetime.combine(day, store.pickup_start, tz)
        close = datetime.combine(day, store.pickup_end, tz)
        slots: list[PickupSlot] = []
        while start + slot_length <= close:
            end = start + slot_length
            if start >= earliest:
                remaining = max(0, store.pickup_slot_capacity - booked.get(start.astimezone(UTC), 0))
                slots.append(
                    PickupSlot(
                        start=start,
                        end=end,
                        label=slot_label(start, end),
                        available=remaining > 0,
                        remaining=remaining,
                    )
                )
            start = end
        result.append(PickupDay(date=day, label=day_label(day, today), slots=slots))
    return result


def resolve_pickup_slot(
    db: Session, store: Store, start: datetime, now: datetime | None = None
) -> PickupSlot:
    if not store.supports_pickup:
        raise AppError(422, "This store doesn't offer pickup")
    if start.tzinfo is None:
        start = start.replace(tzinfo=ZoneInfo(store.timezone))
    for day in pickup_days(db, store, now):
        for slot in day.slots:
            if slot.start == start:
                if not slot.available:
                    raise AppError(409, "That pickup slot just filled up. Please choose another.")
                return slot
    raise AppError(422, "Please choose a valid pickup slot")
