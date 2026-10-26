"""Online payments: Razorpay Checkout (or a simulator in development), webhooks, refunds, expiry.

Flow for an online order:
1. The order is created as PAYMENT_PENDING (stock and pickup slot held).
2. start_payment() creates a Razorpay order; the browser opens Checkout with it.
3. The payment is confirmed by whichever arrives first: the Checkout callback (confirm_razorpay),
   the webhook (handle_webhook) or a status check (reconcile_order). mark_paid() records it once.
4. Unpaid orders are cancelled after PAYMENT_TIMEOUT_MINUTES; a payment that still arrives for a
   cancelled order is refunded automatically.
"""

import logging
import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.types import to_money, utcnow
from app.models import (
    FulfillmentType,
    Order,
    OrderStatus,
    Payment,
    PaymentMethod,
    PaymentState,
    PaymentStatus,
)
from app.schemas.payment import CheckoutPrefill, PaymentInfo, PaymentSessionOut
from app.services.order_state import apply_status, consume_stock_best_effort
from app.services.razorpay import RazorpayClient, RazorpayError, payment_signature_ok, razorpay_client

logger = logging.getLogger("smartcart.payments")
S = OrderStatus
OPEN = (PaymentState.CREATED, PaymentState.FAILED)


def paise(amount: Decimal) -> int:
    return int(to_money(amount) * 100)


def require_online_payments() -> str:
    provider = get_settings().payment_provider
    if provider is None:
        raise AppError(422, "Online payment isn't available yet. Please choose another payment option.")
    return provider


def payment_due(order: Order) -> bool:
    return (
        order.payment_method == PaymentMethod.ONLINE
        and order.payment_status == PaymentStatus.PENDING
        and order.status in (S.PAYMENT_PENDING, S.AWAITING_PAYMENT)
    )


def payment_expires_at(order: Order) -> datetime | None:
    if order.status != S.PAYMENT_PENDING:
        return None
    return order.created_at + timedelta(minutes=get_settings().payment_timeout_minutes)


def payment_info(order: Order) -> PaymentInfo | None:
    payment = order.latest_payment
    if payment is None:
        return None
    return PaymentInfo(
        provider=payment.provider,
        status=payment.status,
        method=payment.method,
        reference=payment.provider_payment_id,
        refund_id=payment.refund_id,
        error=payment.error,
    )


def start_payment(db: Session, order: Order) -> PaymentSessionOut:
    """Returns what Checkout needs, creating a Razorpay order the first time (and reusing it for
    retries, which Razorpay allows until one attempt succeeds)."""
    settings = get_settings()
    provider = require_online_payments()
    if expire_if_overdue(db, order):
        raise AppError(409, "This order was cancelled because the payment wasn't completed in time.")
    if not payment_due(order):
        raise AppError(409, "This order doesn't need a payment.")

    payment = order.latest_payment
    reusable = (
        payment is not None
        and payment.provider == provider
        and payment.status in OPEN
        and payment.amount == order.grand_total
    )
    if not reusable:
        if provider == "razorpay":
            try:
                created = razorpay_client().create_order(
                    paise(order.grand_total),
                    receipt=order.code,
                    notes={"order_code": order.code, "order_id": str(order.id)},
                )
            except RazorpayError as exc:
                logger.error("Razorpay order creation failed for %s: %s", order.code, exc)
                raise AppError(
                    502, "Couldn't reach the payment gateway. Please try again in a moment."
                ) from None
            provider_order_id = created["id"]
        else:
            provider_order_id = f"sim_order_{secrets.token_hex(8)}"
        payment = Payment(
            provider=provider,
            provider_order_id=provider_order_id,
            amount=order.grand_total,
            currency="INR",
            status=PaymentState.CREATED,
        )
        order.payments.append(payment)
        db.commit()

    user = order.user
    return PaymentSessionOut(
        provider=provider,
        key_id=settings.razorpay_key_id if provider == "razorpay" else None,
        provider_order_id=payment.provider_order_id,
        amount=paise(payment.amount),
        currency=payment.currency,
        order_id=order.id,
        order_code=order.code,
        name=settings.app_name,
        description=f"Order {order.code}",
        prefill=CheckoutPrefill(name=user.name, contact=f"+91{user.phone}", email=user.email),
        expires_at=payment_expires_at(order),
    )


def mark_paid(db: Session, payment: Payment, provider_payment_id: str, method: str | None) -> None:
    """Records a successful payment exactly once and moves the order forward. Commits."""
    for attempt in range(3):
        try:
            _mark_paid_once(db, payment, provider_payment_id, method)
            return
        except AppError as exc:
            # The order changed under us (e.g. it expired that very moment). Everything was rolled
            # back, so look again: it will now be moved forward or refunded.
            if exc.status_code != 409 or attempt == 2:
                raise


def _mark_paid_once(db: Session, payment: Payment, provider_payment_id: str, method: str | None) -> None:
    claimed = db.execute(
        update(Payment)
        .where(Payment.id == payment.id, Payment.status.in_(OPEN))
        .values(status=PaymentState.PAID, provider_payment_id=provider_payment_id, method=method, error=None)
        .execution_options(synchronize_session=False)
    ).rowcount
    if claimed != 1:
        db.rollback()
        return  # already recorded: the Checkout callback and the webhook often both arrive
    payment.status = PaymentState.PAID
    payment.provider_payment_id = provider_payment_id
    payment.method = method
    payment.error = None

    order = payment.order
    if order.status == S.CANCELLED or order.payment_status != PaymentStatus.PENDING:
        # Paid after we gave up on the order (it expired or was cancelled), or after it was settled
        # another way (e.g. cash at the counter): give this money back.
        cancelled = order.status == S.CANCELLED
        _refund(payment, "Order was cancelled before the payment arrived" if cancelled else "Already paid")
        if cancelled:
            order.payment_status = PaymentStatus.REFUNDED
        db.commit()
        logger.warning("Refunded late payment %s for order %s", provider_payment_id, order.code)
        return
    order.payment_status = PaymentStatus.PAID
    if order.status == S.PAYMENT_PENDING:
        apply_status(db, order, S.PLACED, note="Paid online")
    elif order.fulfillment_type == FulfillmentType.IN_STORE and order.status == S.AWAITING_PAYMENT:
        consume_stock_best_effort(db, order)
        apply_status(db, order, S.COMPLETED, note="Paid in the app")
    db.commit()


def record_failure(db: Session, payment: Payment, reason: str) -> None:
    if payment.status in OPEN:
        payment.status = PaymentState.FAILED
        payment.error = reason[:300]
        db.commit()


def _captured_details(client: RazorpayClient, payment: Payment, payment_id: str) -> dict[str, Any]:
    details = client.fetch_payment(payment_id)
    if details.get("order_id") != payment.provider_order_id or details.get("amount") != paise(payment.amount):
        raise AppError(400, "Payment details don't match this order.")
    if details.get("status") == "authorized":  # accounts set to manual capture
        details = client.capture(payment_id, paise(payment.amount))
    if details.get("status") != "captured":
        raise AppError(409, "This payment hasn't completed yet.")
    return details


def confirm_razorpay(db: Session, order: Order, payment_id: str, signature: str) -> None:
    """Checkout's success callback. Verifies the signature, then double-checks with Razorpay."""
    payment = order.latest_payment
    if payment is None or payment.provider != "razorpay":
        raise AppError(404, "No Razorpay payment was started for this order.")
    if payment.status == PaymentState.PAID:
        return
    secret = get_settings().razorpay_key_secret or ""
    if not payment_signature_ok(payment.provider_order_id, payment_id, signature, secret):
        raise AppError(400, "We couldn't verify this payment. If money was deducted it will be refunded.")
    try:
        details = _captured_details(razorpay_client(), payment, payment_id)
    except RazorpayError as exc:
        logger.warning("Couldn't confirm payment %s with Razorpay yet: %s", payment_id, exc)
        raise AppError(
            502, "Payment received. We're confirming it with the bank; this will update shortly."
        ) from None
    mark_paid(db, payment, payment_id, details.get("method"))


def complete_simulated(db: Session, order: Order, outcome: str) -> None:
    payment = order.latest_payment
    if get_settings().payment_provider != "simulated" or payment is None or payment.provider != "simulated":
        raise AppError(404, "Simulated payments are turned off.")
    if outcome == "success":
        mark_paid(db, payment, f"sim_pay_{secrets.token_hex(6)}", "simulated")
    else:
        record_failure(db, payment, "Payment declined (simulated)")


def reconcile_order(db: Session, order: Order) -> bool:
    """Asks Razorpay whether an unpaid order was in fact paid, covering a lost callback or webhook."""
    payment = order.latest_payment
    if payment is None or payment.provider != "razorpay" or payment.status not in OPEN:
        return False
    client = razorpay_client()
    try:
        for attempt in client.order_payments(payment.provider_order_id):
            if attempt.get("amount") != paise(payment.amount):
                continue
            if attempt.get("status") == "authorized":
                attempt = client.capture(attempt["id"], paise(payment.amount))
            if attempt.get("status") == "captured":
                mark_paid(db, payment, attempt["id"], attempt.get("method"))
                return True
    except RazorpayError as exc:
        logger.warning("Couldn't check Razorpay order %s: %s", payment.provider_order_id, exc)
    return False


def _refund(payment: Payment, reason: str) -> None:
    """Refunds this one payment in full (Razorpay sends the money back to the original method)."""
    if payment.provider == "razorpay":
        try:
            refund = razorpay_client().refund(
                payment.provider_payment_id or "",
                paise(payment.amount),
                {"order_code": payment.order.code, "reason": reason[:200]},
            )
        except RazorpayError as exc:
            logger.error("Refund failed for payment %s: %s", payment.provider_payment_id, exc)
            raise AppError(
                502, "We couldn't start the refund right now. Please try again in a minute."
            ) from None
        payment.refund_id = refund.get("id")
    else:
        payment.refund_id = f"sim_rfnd_{secrets.token_hex(6)}"
    payment.status = PaymentState.REFUNDED


def refund_order(order: Order, reason: str) -> None:
    """Gives back an order's online payment, if it has one. Raises 502 if the gateway refuses (the
    caller rolls back). Doesn't commit."""
    paid = [payment for payment in order.payments if payment.status == PaymentState.PAID]
    for payment in paid:
        _refund(payment, reason)
    if paid:
        order.payment_status = PaymentStatus.REFUNDED


def _is_overdue(order: Order, now: datetime) -> bool:
    expires_at = payment_expires_at(order)
    return expires_at is not None and now >= expires_at


def _expire(db: Session, order: Order) -> bool:
    try:
        if reconcile_order(db, order):
            return False  # it was paid after all
        apply_status(db, order, S.CANCELLED, note="Payment wasn't completed in time")
    except AppError:
        return False  # somebody else changed it first
    for payment in order.payments:
        if payment.status == PaymentState.CREATED:
            payment.status = PaymentState.FAILED
            payment.error = "Expired before payment"
    db.commit()
    return True


def expire_if_overdue(db: Session, order: Order) -> bool:
    return _is_overdue(order, utcnow()) and _expire(db, order)


def expire_unpaid_orders(db: Session, now: datetime | None = None) -> int:
    """Cancels online orders left unpaid past the timeout and releases their stock and slot."""
    now = now or utcnow()
    cutoff = now - timedelta(minutes=get_settings().payment_timeout_minutes)
    stale = db.scalars(
        select(Order).where(Order.status == S.PAYMENT_PENDING, Order.created_at <= cutoff)
    ).all()
    expired = 0
    for order in stale:
        try:
            expired += _expire(db, order)
        except Exception:  # one bad order mustn't keep the others holding stock
            db.rollback()
            logger.exception("Couldn't expire unpaid order %s", order.code)
    return expired


def handle_webhook(db: Session, event: dict[str, Any]) -> str:
    """Processes a verified Razorpay webhook event. Returns a short outcome for the logs."""
    name = event.get("event", "")
    payload = event.get("payload") or {}
    entity = (payload.get("payment") or {}).get("entity") or {}
    order_entity = (payload.get("order") or {}).get("entity") or {}
    provider_order_id = entity.get("order_id") or order_entity.get("id")
    if not provider_order_id:
        return "ignored"
    payment = db.scalars(select(Payment).where(Payment.provider_order_id == provider_order_id)).first()
    if payment is None:
        return "not ours"
    if name in ("payment.captured", "order.paid"):
        if entity.get("status") != "captured" or entity.get("amount") != paise(payment.amount):
            logger.error("Ignoring %s for %s: unexpected status/amount", name, provider_order_id)
            return "mismatch"
        mark_paid(db, payment, entity["id"], entity.get("method"))
        return "paid"
    if name == "payment.failed":
        record_failure(db, payment, entity.get("error_description") or "Payment failed")
        return "failed"
    return "ignored"
