"""Column types shared by the models."""

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import DateTime, Integer
from sqlalchemy.types import TypeDecorator

PAISE = Decimal("0.01")


def utcnow() -> datetime:
    return datetime.now(UTC)


def to_money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(PAISE, rounding=ROUND_HALF_UP)


class Money(TypeDecorator[Decimal]):
    """Rupee amounts stored as integer paise, so no floating point ever touches money."""

    impl = Integer
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return int(to_money(value) * 100)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return to_money(Decimal(value) / 100)


class UTCDateTime(TypeDecorator[datetime]):
    """Stores naive UTC (portable across SQLite/Postgres) and always returns aware UTC datetimes."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Timezone-aware datetime required")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC)
