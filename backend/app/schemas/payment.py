from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import PaymentState
from app.schemas.common import Schema


class PaymentInfo(Schema):
    provider: str
    status: PaymentState
    method: str | None
    reference: str | None  # the gateway's payment id, e.g. pay_29QQoUBi66xm2f
    refund_id: str | None
    error: str | None


class CheckoutPrefill(Schema):
    name: str | None
    contact: str
    email: str | None


class PaymentSessionOut(Schema):
    """Everything the browser needs to open Razorpay Checkout (or the dev simulator)."""

    provider: Literal["razorpay", "simulated"]
    key_id: str | None
    provider_order_id: str
    amount: int  # paise
    currency: str
    order_id: int
    order_code: str
    name: str
    description: str
    prefill: CheckoutPrefill
    expires_at: datetime | None


class RazorpayVerifyIn(BaseModel):
    razorpay_payment_id: str = Field(min_length=4, max_length=64)
    razorpay_order_id: str = Field(min_length=4, max_length=64)
    razorpay_signature: str = Field(min_length=16, max_length=128)


class SimulatePaymentIn(BaseModel):
    outcome: Literal["success", "failure"] = "success"


class PaymentsConfig(Schema):
    online: bool
    provider: Literal["razorpay", "simulated"] | None
    key_id: str | None
    test_mode: bool


class PublicConfig(Schema):
    app_name: str
    otp_delivery: Literal["sms", "screen"]
    payments: PaymentsConfig
    payment_timeout_minutes: int
    demo: bool  # codes on screen and/or simulated payments: not for real customers yet
