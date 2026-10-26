from fastapi import APIRouter

from app.api.routes import addresses, auth, cart, catalog, instore, orders, payments, staff, stores
from app.core.config import get_settings
from app.schemas.payment import PaymentsConfig, PublicConfig

api_router = APIRouter()


@api_router.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


@api_router.get("/config", response_model=PublicConfig, tags=["meta"])
def public_config():
    """What the web app needs to know about this deployment (no secrets)."""
    settings = get_settings()
    provider = settings.payment_provider
    key_id = settings.razorpay_key_id if provider == "razorpay" else None
    return PublicConfig(
        app_name=settings.app_name,
        otp_delivery="screen" if settings.otp_on_screen else "sms",
        payments=PaymentsConfig(
            online=provider is not None,
            provider=provider,
            key_id=key_id,
            test_mode=provider == "simulated" or (key_id or "").startswith("rzp_test_"),
        ),
        payment_timeout_minutes=settings.payment_timeout_minutes,
        demo=settings.otp_on_screen or provider == "simulated",
    )


for module in (auth, catalog, stores, cart, addresses, orders, payments, instore, staff):
    api_router.include_router(module.router)
