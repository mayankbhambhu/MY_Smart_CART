from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app.core.errors import AppError
from app.models import Order, Store
from app.services.slots import pickup_days, resolve_pickup_slot

IST = ZoneInfo("Asia/Kolkata")


def _now(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 26, hour, minute, tzinfo=IST).astimezone(UTC)


def _book(db, store: Store, start: datetime, count: int) -> None:
    for i in range(count):
        db.add(
            Order(
                code=f"T{start:%H%M}{i:03d}",
                user_id=1,
                store_id=store.id,
                fulfillment_type="pickup",
                status="placed",
                payment_method="pay_at_store",
                pickup_slot_start=start,
                pickup_slot_end=start + timedelta(minutes=30),
                item_total=Decimal(10),
                mrp_total=Decimal(10),
                grand_total=Decimal(12),
            )
        )
    db.commit()


def test_slots_respect_hours_and_lead_time(db):
    store = db.get(Store, 1)  # pickup counter 08:00-22:00, 30 min slots
    days = pickup_days(db, store, now=_now(10, 10), days=3)

    assert [d.label for d in days[:2]] == ["Today", "Tomorrow"]
    assert days[2].label == datetime(2026, 10, 28).strftime("%a, %d %b")
    today = days[0].slots
    assert today[0].label == "11:00 AM – 11:30 AM"  # 10:30 is inside the 30 min prep window
    assert today[-1].label == "9:30 PM – 10:00 PM"
    tomorrow = days[1].slots
    assert tomorrow[0].label == "8:00 AM – 8:30 AM" and len(tomorrow) == 28


def test_no_slots_left_today_after_closing(db):
    days = pickup_days(db, db.get(Store, 1), now=_now(21, 50), days=2)
    assert days[0].slots == []
    assert days[1].slots


def test_capacity_and_full_slots(db):
    store = db.get(Store, 1)
    slot_start = datetime(2026, 10, 26, 12, 0, tzinfo=IST)
    _book(db, store, slot_start, store.pickup_slot_capacity - 1)

    slot = next(s for s in pickup_days(db, store, now=_now(10))[0].slots if s.start == slot_start)
    assert slot.remaining == 1 and slot.available
    assert resolve_pickup_slot(db, store, slot_start, now=_now(10)).start == slot_start

    _book(db, store, slot_start + timedelta(hours=1), store.pickup_slot_capacity)
    with pytest.raises(AppError) as full:
        resolve_pickup_slot(db, store, slot_start + timedelta(hours=1), now=_now(10))
    assert full.value.status_code == 409


def test_invalid_slots_are_rejected(db):
    store = db.get(Store, 1)
    for bad in [
        datetime(2026, 10, 26, 10, 15, tzinfo=IST),  # not on a slot boundary
        datetime(2026, 10, 26, 9, 0, tzinfo=IST),  # already passed
        datetime(2026, 10, 26, 23, 0, tzinfo=IST),  # counter closed
        datetime(2026, 11, 20, 12, 0, tzinfo=IST),  # too far ahead
    ]:
        with pytest.raises(AppError) as err:
            resolve_pickup_slot(db, store, bad, now=_now(10))
        assert err.value.status_code == 422
