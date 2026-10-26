from pydantic import BaseModel, Field

from app.models.enums import UserRole
from app.schemas.common import Schema


class OtpRequestIn(BaseModel):
    phone: str = Field(max_length=20, examples=["9876543210"])


class OtpRequestOut(Schema):
    phone: str
    expires_in: int
    resend_in: int
    # Only populated when OTP_DEV_MODE is on (no SMS provider configured).
    dev_otp: str | None = None


class OtpVerifyIn(BaseModel):
    phone: str = Field(max_length=20)
    otp: str = Field(min_length=4, max_length=8, pattern=r"^\d+$")


class UserOut(Schema):
    id: int
    phone: str
    name: str | None
    email: str | None
    role: UserRole
    store_id: int | None


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class TokenOut(Schema):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    is_new_user: bool
