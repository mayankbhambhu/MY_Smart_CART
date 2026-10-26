import base64
from datetime import timedelta
from urllib.parse import parse_qs

import httpx2
import pytest
from sqlalchemy import func, select, update

from app.core.config import get_settings
from app.core.ratelimit import SlidingWindowLimiter
from app.core.types import utcnow
from app.models import OtpRequest
from app.services import outbound, sms

PHONE = "9811122233"


class FakeGateway:
    """Stands in for MSG91 / Twilio: records what we send and answers with `reply`."""

    def __init__(self):
        self.requests: list[httpx2.Request] = []
        self.reply = httpx2.Response(200, json={"type": "success", "request_id": "3561626b6c6e313233343536"})

    def handler(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


@pytest.fixture
def gateway(monkeypatch) -> FakeGateway:
    fake = FakeGateway()
    monkeypatch.setattr(
        outbound, "client", lambda: httpx2.Client(transport=httpx2.MockTransport(fake.handler))
    )
    return fake


@pytest.fixture
def msg91(monkeypatch, gateway) -> FakeGateway:
    settings = get_settings()
    monkeypatch.setattr(settings, "sms_provider", "msg91")
    monkeypatch.setattr(settings, "msg91_auth_key", "msg91-auth-key")
    monkeypatch.setattr(settings, "msg91_otp_template_id", "6650c1d2d6fc05214e3b8a42")
    return gateway


@pytest.fixture
def twilio(monkeypatch, gateway) -> FakeGateway:
    settings = get_settings()
    monkeypatch.setattr(settings, "sms_provider", "twilio")
    monkeypatch.setattr(settings, "twilio_account_sid", "AC0123456789abcdef")
    monkeypatch.setattr(settings, "twilio_auth_token", "twilio-token")
    monkeypatch.setattr(settings, "twilio_from", "+15005550006")
    gateway.reply = httpx2.Response(201, json={"sid": "SM0123", "status": "queued"})
    return gateway


def _request_otp(client, phone: str = PHONE):
    return client.post("/api/auth/otp/request", json={"phone": phone})


def _stored(db) -> int:
    return db.scalar(select(func.count()).select_from(OtpRequest))


def test_console_mode_shows_the_code_on_screen(client):
    body = _request_otp(client).json()
    assert body["delivery"] == "screen" and len(body["dev_otp"]) == 6
    config = client.get("/api/config").json()
    assert config["otp_delivery"] == "screen" and config["demo"] is True


def test_msg91_sends_the_code_by_sms(client, msg91):
    res = _request_otp(client)
    assert res.status_code == 200, res.text
    assert res.json()["delivery"] == "sms" and res.json()["dev_otp"] is None  # never leaked to the browser

    [sent] = msg91.requests
    assert sent.method == "POST" and str(sent.url).startswith("https://control.msg91.com/api/v5/otp?")
    assert sent.headers["authkey"] == "msg91-auth-key"
    params = sent.url.params
    assert params["template_id"] == "6650c1d2d6fc05214e3b8a42"
    assert params["mobile"] == f"91{PHONE}"
    assert params["otp_length"] == "6" and params["otp_expiry"] == "5"
    code = params["otp"]

    verified = client.post("/api/auth/otp/verify", json={"phone": PHONE, "otp": code})
    assert verified.status_code == 200
    assert client.get("/api/config").json()["otp_delivery"] == "sms"


def test_msg91_refusal_is_reported_and_retry_allowed(client, db, msg91):
    # MSG91 says no with HTTP 200 and an error body.
    msg91.reply = httpx2.Response(200, json={"type": "error", "message": "Invalid authkey"})
    res = _request_otp(client)
    assert res.status_code == 502
    assert "couldn't send the SMS" in res.json()["detail"]
    assert _stored(db) == 0

    msg91.reply = httpx2.Response(200, json={"type": "success"})
    assert _request_otp(client).status_code == 200  # no cooldown: nothing was sent before


def test_twilio_sends_the_code_by_sms(client, twilio, monkeypatch):
    monkeypatch.setattr(get_settings(), "webotp_domain", "smartcart.example")
    assert _request_otp(client).status_code == 200

    [sent] = twilio.requests
    assert sent.url.path == "/2010-04-01/Accounts/AC0123456789abcdef/Messages.json"
    assert (
        sent.headers["authorization"]
        == "Basic " + base64.b64encode(b"AC0123456789abcdef:twilio-token").decode()
    )
    form = {key: values[0] for key, values in parse_qs(sent.content.decode()).items()}
    assert form["To"] == f"+91{PHONE}" and form["From"] == "+15005550006"
    code = form["Body"][:6]
    assert code.isdigit() and form["Body"].endswith(f"@smartcart.example #{code}")  # WebOTP autofill line
    assert client.post("/api/auth/otp/verify", json={"phone": PHONE, "otp": code}).status_code == 200

    monkeypatch.setattr(get_settings(), "twilio_from", "MG0123456789abcdef")
    assert _request_otp(client, "9811122244").status_code == 200
    form = parse_qs(twilio.requests[-1].content.decode())
    assert form["MessagingServiceSid"] == ["MG0123456789abcdef"] and "From" not in form


def test_twilio_failures_are_reported(client, db, twilio):
    twilio.reply = httpx2.Response(400, json={"code": 21211, "message": "Invalid 'To' Phone Number"})
    assert _request_otp(client).status_code == 502
    twilio.reply = httpx2.ConnectError("connection refused")
    assert _request_otp(client).status_code == 502
    assert _stored(db) == 0


def test_codes_per_number_are_capped_per_hour(client, db):
    for _ in range(get_settings().otp_max_per_phone_per_hour):
        assert _request_otp(client).status_code == 200
        db.execute(update(OtpRequest).values(created_at=utcnow() - timedelta(minutes=2)))  # skip cooldown
        db.commit()
    capped = _request_otp(client)
    assert capped.status_code == 429 and "Too many codes" in capped.json()["detail"]

    db.execute(update(OtpRequest).values(created_at=utcnow() - timedelta(minutes=61)))
    db.commit()
    assert _request_otp(client).status_code == 200


def test_codes_per_network_are_capped(client):
    client.app.state.otp_ip_limiter = SlidingWindowLimiter(2, 3600)
    assert _request_otp(client, "9811100001").status_code == 200
    assert _request_otp(client, "9811100002").status_code == 200
    blocked = _request_otp(client, "9811100003")
    assert blocked.status_code == 429 and "network" in blocked.json()["detail"]


def test_codes_overall_are_capped(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "otp_max_per_hour", 2)
    assert _request_otp(client, "9811100001").status_code == 200
    assert _request_otp(client, "9811100002").status_code == 200
    assert _request_otp(client, "9811100003").status_code == 503


class FakeVerifyNow:
    """Message Central VerifyNow: issues auth tokens, sends its own codes and checks them."""

    def __init__(self):
        self.requests: list[httpx2.Request] = []
        self.codes: dict[str, str] = {}  # verificationId -> code it "sent"
        self.expired: set[str] = set()
        self.valid_tokens: set[str] = set()
        self.token_fetches = 0
        self.validate_reply: httpx2.Response | None = None  # override to misbehave

    def handler(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        params = request.url.params
        if request.url.path == "/auth/v1/authentication/token":
            assert params["key"] == base64.b64encode(b"mc-password").decode() and params["scope"] == "NEW"
            self.token_fetches += 1
            token = f"token-{self.token_fetches}"
            self.valid_tokens.add(token)
            return httpx2.Response(200, json={"status": 200, "token": token})
        if request.headers.get("authToken") not in self.valid_tokens:
            return httpx2.Response(401, json={"responseCode": 401, "message": "UNAUTHORIZED"})
        assert params["customerId"] == "C-TEST123" and params["countryCode"] == "91"
        if request.url.path == "/verification/v3/send":
            verification_id = str(4_000_000 + len(self.codes))
            self.codes[verification_id] = "4" * int(params["otpLength"])
            data = {
                "verificationId": verification_id,
                "mobileNumber": params["mobileNumber"],
                "timeout": "60",
            }
            return httpx2.Response(200, json={"responseCode": 200, "message": "SUCCESS", "data": data})
        if request.url.path == "/verification/v3/validateOtp":
            if self.validate_reply is not None:
                return self.validate_reply
            verification_id = params["verificationId"]
            if verification_id in self.expired:
                return httpx2.Response(400, json={"responseCode": 705, "message": "VERIFICATION_EXPIRED"})
            if params["code"] != self.codes[verification_id]:
                return httpx2.Response(400, json={"responseCode": 702, "message": "WRONG_OTP_PROVIDED"})
            data = {"verificationId": verification_id, "verificationStatus": "VERIFICATION_COMPLETED"}
            return httpx2.Response(200, json={"responseCode": 200, "message": "SUCCESS", "data": data})
        return httpx2.Response(404)


@pytest.fixture
def verifynow(monkeypatch) -> FakeVerifyNow:
    settings = get_settings()
    monkeypatch.setattr(settings, "sms_provider", "messagecentral")
    monkeypatch.setattr(settings, "messagecentral_customer_id", "C-TEST123")
    monkeypatch.setattr(settings, "messagecentral_password", "mc-password")
    fake = FakeVerifyNow()
    monkeypatch.setattr(
        outbound, "client", lambda: httpx2.Client(transport=httpx2.MockTransport(fake.handler))
    )
    sms._verifynow_token.forget()
    yield fake
    sms._verifynow_token.forget()


def _verify(client, code: str, phone: str = PHONE):
    return client.post("/api/auth/otp/verify", json={"phone": phone, "otp": code})


def test_messagecentral_sends_and_checks_its_own_code(client, verifynow):
    sent = _request_otp(client)
    assert sent.status_code == 200, sent.text
    assert sent.json()["delivery"] == "sms" and sent.json()["dev_otp"] is None
    assert sent.json()["resend_in"] == 60  # VerifyNow won't send another code sooner

    send = next(r for r in verifynow.requests if r.url.path == "/verification/v3/send")
    assert send.method == "POST" and send.url.params["mobileNumber"] == PHONE
    assert send.url.params["otpLength"] == "6" and send.url.params["flowType"] == "SMS"
    [(verification_id, code)] = verifynow.codes.items()

    assert _verify(client, "123456").status_code == 400  # wrong code: checked by the provider
    login = _verify(client, code)
    assert login.status_code == 200 and login.json()["access_token"]
    check = [r for r in verifynow.requests if r.url.path == "/verification/v3/validateOtp"][-1]
    assert check.url.params["verificationId"] == verification_id
    assert _verify(client, code).status_code == 400  # used up

    too_soon = _request_otp(client)
    assert too_soon.status_code == 429 and too_soon.json()["details"]["retry_after"] > 30


def test_messagecentral_expired_code(client, verifynow):
    _request_otp(client)
    [(verification_id, code)] = verifynow.codes.items()
    verifynow.expired.add(verification_id)
    expired = _verify(client, code)
    assert expired.status_code == 400 and "expired" in expired.json()["detail"]
    assert _verify(client, code).status_code == 400  # stays expired on our side too


def test_messagecentral_renews_its_auth_token(client, verifynow):
    assert _request_otp(client, "9811100001").status_code == 200
    verifynow.valid_tokens.clear()  # the day-old token has expired
    assert _request_otp(client, "9811100002").status_code == 200
    assert verifynow.token_fetches == 2


def test_messagecentral_odd_answers_never_log_anyone_in(client, db, verifynow):
    _request_otp(client)
    [(_, code)] = verifynow.codes.items()
    verifynow.validate_reply = httpx2.Response(200, json={"responseCode": 200, "message": "SUCCESS"})
    assert _verify(client, code).status_code == 502

    verifynow.validate_reply = httpx2.Response(500, text="<html>Bad gateway</html>")
    assert _verify(client, code).status_code == 502

    original = verifynow.handler

    def refuse_sends(request):
        if request.url.path == "/verification/v3/send":
            return httpx2.Response(200, json={"responseCode": 511, "message": "INVALID_COUNTRY_CODE"})
        return original(request)

    verifynow.handler = refuse_sends
    before = _stored(db)
    assert _request_otp(client, "9811100009").status_code == 502
    assert _stored(db) == before
