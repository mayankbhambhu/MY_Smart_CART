"""Login codes by SMS. Choose the gateway with SMS_PROVIDER.

- console: logs the code (the API also returns it so the login screen can show it). Dev/demo only.
- msg91:   MSG91's OTP API. In India every SMS must use a DLT-approved template; create an OTP
           template containing ##OTP## in the MSG91 panel and set MSG91_OTP_TEMPLATE_ID.
- twilio:  Twilio Programmable Messaging. For Indian numbers Twilio also needs your DLT sender ID
           and template registered, and the body below must match that template.
"""

import logging

import httpx2

from app.core.config import Settings, get_settings
from app.services import outbound

logger = logging.getLogger("smartcart.sms")

MSG91_OTP_URL = "https://control.msg91.com/api/v5/otp"
TWILIO_MESSAGES_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


class SmsError(Exception):
    """The gateway didn't accept the message."""


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


def send_otp(phone: str, code: str) -> None:
    """Delivers a login code to a 10-digit Indian mobile number. Raises SmsError on failure."""
    settings = get_settings()
    if settings.sms_provider == "console":
        logger.info("Login code for %s: %s (SMS_PROVIDER=console, nothing sent)", phone, code)
        return
    try:
        with outbound.client() as http:
            if settings.sms_provider == "msg91":
                _send_msg91(http, settings, phone, code)
            else:
                _send_twilio(http, settings, phone, code)
    except httpx2.HTTPError as exc:
        raise SmsError(f"Couldn't reach {settings.sms_provider}: {exc}") from exc
    logger.info("Login code sent to %s via %s", masked(phone), settings.sms_provider)
