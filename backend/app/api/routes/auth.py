from datetime import timedelta

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    generate_numeric_code,
    hash_otp,
    normalize_phone,
    otp_matches,
)
from app.core.types import utcnow
from app.models import OtpRequest, User
from app.schemas.auth import OtpRequestIn, OtpRequestOut, OtpVerifyIn, TokenOut, UserOut, UserUpdate
from app.services.notifications import send_otp_sms

router = APIRouter(prefix="/auth", tags=["auth"])


def _valid_phone(raw: str) -> str:
    phone = normalize_phone(raw)
    if phone is None:
        raise AppError(422, "Enter a valid 10-digit mobile number")
    return phone


@router.post("/otp/request", response_model=OtpRequestOut)
def request_otp(body: OtpRequestIn, db: DbSession):
    settings = get_settings()
    phone = _valid_phone(body.phone)
    now = utcnow()

    last = db.scalars(
        select(OtpRequest).where(OtpRequest.phone == phone).order_by(OtpRequest.id.desc()).limit(1)
    ).first()
    if last is not None:
        wait = settings.otp_resend_cooldown_seconds - int((now - last.created_at).total_seconds())
        if wait > 0:
            raise AppError(429, f"Please wait {wait}s before requesting a new OTP", {"retry_after": wait})

    code = generate_numeric_code(settings.otp_length)
    db.add(
        OtpRequest(
            phone=phone,
            code_hash=hash_otp(phone, code),
            created_at=now,
            expires_at=now + timedelta(seconds=settings.otp_ttl_seconds),
        )
    )
    db.commit()
    send_otp_sms(phone, code)
    return OtpRequestOut(
        phone=phone,
        expires_in=settings.otp_ttl_seconds,
        resend_in=settings.otp_resend_cooldown_seconds,
        dev_otp=code if settings.otp_dev_mode else None,
    )


@router.post("/otp/verify", response_model=TokenOut)
def verify_otp(body: OtpVerifyIn, db: DbSession):
    settings = get_settings()
    phone = _valid_phone(body.phone)
    now = utcnow()

    otp = db.scalars(
        select(OtpRequest).where(OtpRequest.phone == phone).order_by(OtpRequest.id.desc()).limit(1)
    ).first()
    if otp is None or otp.consumed_at is not None or otp.expires_at <= now:
        raise AppError(400, "OTP expired. Please request a new one.")
    if otp.attempts >= settings.otp_max_attempts:
        raise AppError(429, "Too many incorrect attempts. Please request a new OTP.")
    if not otp_matches(phone, body.otp, otp.code_hash):
        otp.attempts += 1
        db.commit()
        raise AppError(400, "Incorrect OTP. Please try again.")

    otp.consumed_at = now
    user = db.scalars(select(User).where(User.phone == phone)).first()
    is_new = user is None
    if user is None:
        user = User(phone=phone)
        db.add(user)
    db.commit()
    return TokenOut(
        access_token=create_access_token(user.id),
        user=UserOut.model_validate(user),
        is_new_user=is_new,
    )


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(body: UserUpdate, user: CurrentUser, db: DbSession):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    return user
