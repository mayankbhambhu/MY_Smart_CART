import json
import logging

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from app.api.deps import CurrentUser, DbSession
from app.api.routes.orders import own_order
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.errors import AppError
from app.schemas.order import OrderOut
from app.schemas.payment import PaymentSessionOut, RazorpayVerifyIn, SimulatePaymentIn
from app.services import payments
from app.services.orders import order_out
from app.services.razorpay import webhook_signature_ok

logger = logging.getLogger("smartcart.payments")
router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/orders/{order_id}/session", response_model=PaymentSessionOut)
def payment_session(order_id: int, user: CurrentUser, db: DbSession):
    """Starts (or resumes) paying for an order: returns the options for Razorpay Checkout."""
    return payments.start_payment(db, own_order(db, user, order_id))


@router.post("/orders/{order_id}/razorpay/verify", response_model=OrderOut)
def verify_razorpay(order_id: int, body: RazorpayVerifyIn, user: CurrentUser, db: DbSession):
    """Called with what Razorpay Checkout hands back after a successful payment."""
    order = own_order(db, user, order_id)
    payments.confirm_razorpay(db, order, body.razorpay_payment_id, body.razorpay_signature)
    return order_out(order)


@router.post("/orders/{order_id}/refresh", response_model=OrderOut)
def refresh_payment(order_id: int, user: CurrentUser, db: DbSession):
    """Re-checks an unpaid order with Razorpay (e.g. the customer paid but closed the tab)."""
    order = own_order(db, user, order_id)
    if payments.payment_due(order):
        payments.reconcile_order(db, order) or payments.expire_if_overdue(db, order)
    return order_out(order)


@router.post("/orders/{order_id}/simulate", response_model=OrderOut)
def simulate_payment(order_id: int, body: SimulatePaymentIn, user: CurrentUser, db: DbSession):
    """Development only (no Razorpay keys): pretend the customer paid, or that it failed."""
    order = own_order(db, user, order_id)
    payments.complete_simulated(db, order, body.outcome)
    return order_out(order)


def _process_webhook(event: dict) -> str:
    with SessionLocal() as db:
        return payments.handle_webhook(db, event)


@router.post("/razorpay/webhook")
async def razorpay_webhook(request: Request):
    """Razorpay → us. Set the URL and secret under Dashboard → Webhooks (events: payment.captured,
    order.paid, payment.failed). The body is verified byte-for-byte before it's parsed."""
    secret = get_settings().razorpay_webhook_secret
    if not secret:
        raise AppError(404, "Webhooks aren't set up")
    raw_body = await request.body()
    if not webhook_signature_ok(raw_body, request.headers.get("x-razorpay-signature", ""), secret):
        raise AppError(400, "Invalid webhook signature")
    try:
        event = json.loads(raw_body)
    except ValueError:
        raise AppError(400, "Webhook body isn't JSON") from None
    outcome = await run_in_threadpool(_process_webhook, event)
    logger.info("Razorpay webhook %s: %s", event.get("event"), outcome)
    return {"status": "ok"}
