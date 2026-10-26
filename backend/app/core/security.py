import hashlib
import hmac
import re
import secrets
from datetime import timedelta

import jwt

from app.core.config import get_settings
from app.core.types import utcnow

ALGORITHM = "HS256"
_PHONE_RE = re.compile(r"^[6-9]\d{9}$")


def normalize_phone(raw: str) -> str | None:
    """Accepts Indian mobile numbers like '98765 43210', '+91-9876543210', '09876543210'
    and returns the bare 10-digit number, or None if it isn't a valid mobile number."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits if _PHONE_RE.match(digits) else None


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def generate_numeric_code(length: int) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


def hash_otp(phone: str, code: str) -> str:
    key = get_settings().secret_key.encode()
    return hmac.new(key, f"{phone}:{code}".encode(), hashlib.sha256).hexdigest()


def otp_matches(phone: str, code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(phone, code), code_hash)
