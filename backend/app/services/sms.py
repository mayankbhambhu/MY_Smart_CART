"""Login codes by SMS. Choose the gateway with SMS_PROVIDER.

- console: logs the code (the API also returns it so the login screen can show it). Dev/demo only.
- messagecentral: Message Central VerifyNow. It sends its own code from its own DLT-approved
           template and checks it for us, so it works without your own DLT registration.
- msg91:   MSG91's OTP API. In India every SMS must use a DLT-approved template; create an OTP
           template containing ##OTP## in the MSG91 panel and set MSG91_OTP_TEMPLATE_ID.
- twilio:  Twilio Programmable Messaging. For Indian numbers Twilio also needs your DLT sender ID
           and template registered, and the body below must match that template.
"""

import base64
import logging
import threading
import time
from typing import Literal

import httpx2

from app.core.config import Settings, get_settings
from app.services import outbound

logger = logging.getLogger("smartcart.sms")

MSG91_OTP_URL = "https://control.msg91.com/api/v5/otp"
TWILIO_MESSAGES_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

CodeCheck = Literal["ok", "wrong", "expired"]


class SmsError(Exception):
    """The gateway didn't accept the message (or couldn't be asked)."""


def masked(phone: str) -> str:
    return f"{phone[:2]}******{phone[-2:]}"


def otp_message(code: str, settings: Settings) -> str:
    minutes = max(1, settings.otp_ttl_seconds // 60)
    text = (
        f"{code} is your {settings.app_name} login code. It expires in {minutes} minutes. "
        "Don't share it with anyone."
    )
    if settings.webotp_domain:
        # WebOTP format: lets Chrome on Android offer to fill the code in automatically.
        text += f"\n\n@{settings.webotp_domain} #{code}"
    return text


def _json(response: httpx2.Response) -> dict:
    try:
        data = response.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _send_msg91(http: httpx2.Client, settings: Settings, phone: str, code: str) -> None:
    response = http.post(
        MSG91_OTP_URL,
        params={
            "template_id": settings.msg91_otp_template_id,
            "mobile": f"91{phone}",
            "otp": code,
            "otp_length": len(code),
            "otp_expiry": max(1, settings.otp_ttl_seconds // 60),
        },
        headers={"authkey": settings.msg91_auth_key or "", "accept": "application/json"},
        json={},
    )
    data = _json(response)
    # MSG91 answers HTTP 200 even when it refuses; the body says {"type": "error", "message": ...}.
    if response.status_code >= 400 or data.get("type") != "success":
        raise SmsError(f"MSG91 refused the OTP: {data.get('message') or f'HTTP {response.status_code}'}")


def _send_twilio(http: httpx2.Client, settings: Settings, phone: str, code: str) -> None:
    sender = settings.twilio_from or ""
    form = {"To": f"+91{phone}", "Body": otp_message(code, settings)}
    form["MessagingServiceSid" if sender.startswith("MG") else "From"] = sender
    response = http.post(
        TWILIO_MESSAGES_URL.format(sid=settings.twilio_account_sid),
        data=form,
        auth=(settings.twilio_account_sid or "", settings.twilio_auth_token or ""),
    )
    if response.status_code >= 400:
        message = _json(response).get("message") or f"HTTP {response.status_code}"
        raise SmsError(f"Twilio refused the SMS: {message}")


# ---- Message Central VerifyNow ----------------------------------------------------------------
# https://www.messagecentral.com/product/verify-now/api-india
# The provider generates the code, so we keep its verificationId and ask it to check what the
# customer types. Anything we don't recognise counts as a failure: a login is never let through
# on an unexpected answer.


class _VerifyNowToken:
    """Auth tokens last about a day; we fetch one when needed and renew it well before then."""

    max_age_seconds = 6 * 3600

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._value: str | None = None
        self._fetched_at = 0.0

    def get(self, http: httpx2.Client, settings: Settings, renew: bool = False) -> str:
        with self._lock:
            fresh = time.monotonic() - self._fetched_at < self.max_age_seconds
            if self._value and fresh and not renew:
                return self._value
            password = (settings.messagecentral_password or "").encode()
            params = {
                "customerId": settings.messagecentral_customer_id,
                "key": base64.b64encode(password).decode(),
                "scope": "NEW",
                "country": "91",
            }
            if settings.messagecentral_email:
                params["email"] = settings.messagecentral_email
            response = http.get(
                f"{settings.messagecentral_api_base}/auth/v1/authentication/token", params=params
            )
            data = _json(response)
            token = data.get("token")
            if response.status_code >= 400 or not isinstance(token, str) or not token:
                raise SmsError(
                    f"Message Central login failed: {data.get('message') or f'HTTP {response.status_code}'}"
                )
            self._value, self._fetched_at = token, time.monotonic()
            return token

    def forget(self) -> None:
        with self._lock:
            self._value = None


_verifynow_token = _VerifyNowToken()


def _verifynow(
    http: httpx2.Client, settings: Settings, method: str, path: str, params: dict
) -> tuple[httpx2.Response, dict]:
    """Calls VerifyNow, renewing the auth token once if it has expired."""
    params = {"countryCode": "91", "customerId": settings.messagecentral_customer_id, **params}
    for renew in (False, True):
        token = _verifynow_token.get(http, settings, renew=renew)
        response = http.request(
            method, f"{settings.messagecentral_api_base}{path}", params=params, headers={"authToken": token}
        )
        if response.status_code != 401:
            break
    return response, _json(response)


def _verifynow_code(data: dict) -> str:
    inner = data.get("data") if isinstance(data.get("data"), dict) else {}
    return str(data.get("responseCode") or inner.get("responseCode") or "")


def _verifynow_error(response: httpx2.Response, data: dict) -> str:
    inner = data.get("data") if isinstance(data.get("data"), dict) else {}
    detail = inner.get("errorMessage") or data.get("message") or f"HTTP {response.status_code}"
    return f"{detail} (code {_verifynow_code(data) or '?'})"


def _send_verifynow(http: httpx2.Client, settings: Settings, phone: str) -> str:
    response, data = _verifynow(
        http,
        settings,
        "POST",
        "/verification/v3/send",
        {"flowType": "SMS", "mobileNumber": phone, "otpLength": settings.otp_length},
    )
    inner = data.get("data") if isinstance(data.get("data"), dict) else {}
    verification_id = inner.get("verificationId")
    if response.status_code >= 400 or _verifynow_code(data) != "200" or not verification_id:
        raise SmsError(f"Message Central refused the OTP: {_verifynow_error(response, data)}")
    return str(verification_id)


# VerifyNow response codes for a code that doesn't log the customer in.
_VERIFYNOW_WRONG = {"702", "700"}  # wrong code / verification failed
_VERIFYNOW_EXPIRED = {"705", "703", "800"}  # expired / already used / too many attempts


def _check_verifynow(
    http: httpx2.Client, settings: Settings, phone: str, reference: str, code: str
) -> CodeCheck:
    response, data = _verifynow(
        http,
        settings,
        "GET",
        "/verification/v3/validateOtp",
        {"mobileNumber": phone, "verificationId": reference, "code": code},
    )
    inner = data.get("data") if isinstance(data.get("data"), dict) else {}
    status = _verifynow_code(data)
    if (
        response.status_code == 200
        and status == "200"
        and inner.get("verificationStatus") == "VERIFICATION_COMPLETED"
    ):
        return "ok"
    if status in _VERIFYNOW_WRONG:
        return "wrong"
    if status in _VERIFYNOW_EXPIRED:
        return "expired"
    raise SmsError(f"Message Central couldn't check the code: {_verifynow_error(response, data)}")


# ---- What the login routes call ----------------------------------------------------------------


def send_otp(phone: str, code: str) -> str | None:
    """Delivers a login code to a 10-digit Indian mobile number. Raises SmsError on failure.

    Returns the provider's reference when the provider generated and will check its own code
    (Message Central); `code` is then unused. Otherwise returns None and we check `code` ourselves."""
    settings = get_settings()
    if settings.sms_provider == "console":
        logger.info("Login code for %s: %s (SMS_PROVIDER=console, nothing sent)", phone, code)
        return None
    reference = None
    try:
        with outbound.client() as http:
            if settings.sms_provider == "messagecentral":
                reference = _send_verifynow(http, settings, phone)
            elif settings.sms_provider == "msg91":
                _send_msg91(http, settings, phone, code)
            else:
                _send_twilio(http, settings, phone, code)
    except httpx2.HTTPError as exc:
        raise SmsError(f"Couldn't reach {settings.sms_provider}: {exc}") from exc
    logger.info("Login code sent to %s via %s", masked(phone), settings.sms_provider)
    return reference


def check_otp(phone: str, reference: str, code: str) -> CodeCheck:
    """Asks the provider whether `code` is right for the code it sent (see send_otp)."""
    settings = get_settings()
    try:
        with outbound.client() as http:
            return _check_verifynow(http, settings, phone, reference, code)
    except httpx2.HTTPError as exc:
        raise SmsError(f"Couldn't reach {settings.sms_provider}: {exc}") from exc
