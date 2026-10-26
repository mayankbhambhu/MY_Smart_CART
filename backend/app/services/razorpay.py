"""A small Razorpay REST client covering what this app needs, plus signature checks.

API reference: https://razorpay.com/docs/api/ (Orders, Payments, Refunds). All amounts are in paise."""

import hashlib
import hmac
from typing import Any

import httpx2

from app.core.config import get_settings
from app.services import outbound


class RazorpayError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _hmac_hex(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def payment_signature_ok(order_id: str, payment_id: str, signature: str, secret: str) -> bool:
    """Checkout returns a signature over "<order_id>|<payment_id>"; only Razorpay can produce it.
    Always pass the order id stored on our side, never the one the browser sent back."""
    return hmac.compare_digest(_hmac_hex(secret, f"{order_id}|{payment_id}".encode()), signature or "")


def webhook_signature_ok(raw_body: bytes, signature: str, secret: str) -> bool:
    """Webhooks are signed over the exact request bytes with the webhook secret."""
    return hmac.compare_digest(_hmac_hex(secret, raw_body), signature or "")


class RazorpayClient:
    def __init__(self, key_id: str, key_secret: str, base_url: str):
        self.key_id = key_id
        self.key_secret = key_secret
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: dict | None = None) -> dict[str, Any]:
        try:
            with outbound.client() as http:
                response = http.request(
                    method, f"{self.base_url}{path}", json=body, auth=(self.key_id, self.key_secret)
                )
        except httpx2.HTTPError as exc:
            raise RazorpayError(f"Couldn't reach Razorpay: {exc}") from exc
        try:
            data = response.json() if response.content else {}
        except ValueError:
            data = {}
        if response.status_code >= 400:
            error = data.get("error") if isinstance(data, dict) else None
            description = error.get("description") if isinstance(error, dict) else None
            raise RazorpayError(
                description or f"Razorpay returned HTTP {response.status_code}", response.status_code
            )
        return data

    def create_order(self, amount_paise: int, receipt: str, notes: dict[str, str]) -> dict[str, Any]:
        return self._request(
            "POST", "/orders", {"amount": amount_paise, "currency": "INR", "receipt": receipt, "notes": notes}
        )

    def fetch_payment(self, payment_id: str) -> dict[str, Any]:
        return self._request("GET", f"/payments/{payment_id}")

    def order_payments(self, order_id: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/orders/{order_id}/payments").get("items", [])

    def capture(self, payment_id: str, amount_paise: int) -> dict[str, Any]:
        return self._request(
            "POST", f"/payments/{payment_id}/capture", {"amount": amount_paise, "currency": "INR"}
        )

    def refund(self, payment_id: str, amount_paise: int, notes: dict[str, str]) -> dict[str, Any]:
        return self._request(
            "POST", f"/payments/{payment_id}/refund", {"amount": amount_paise, "notes": notes}
        )


def razorpay_client() -> RazorpayClient:
    settings = get_settings()
    return RazorpayClient(
        settings.razorpay_key_id or "", settings.razorpay_key_secret or "", settings.razorpay_api_base
    )
