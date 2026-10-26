from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Schema


class AddressIn(BaseModel):
    label: Literal["Home", "Work", "Other"] = "Home"
    receiver_name: str = Field(min_length=1, max_length=80)
    receiver_phone: str | None = Field(default=None, max_length=15)
    house: str = Field(min_length=1, max_length=120)
    area: str = Field(min_length=1, max_length=160)
    landmark: str | None = Field(default=None, max_length=120)
    city: str = Field(min_length=1, max_length=60)
    pincode: str = Field(pattern=r"^\d{6}$")
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    is_default: bool = False


class AddressOut(Schema):
    id: int
    label: str
    receiver_name: str
    receiver_phone: str | None
    house: str
    area: str
    landmark: str | None
    city: str
    pincode: str
    lat: float
    lng: float
    is_default: bool
