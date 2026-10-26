import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db, utcnow
from ..models import OtpCode, User
from ..schemas import OtpRequest, OtpRequestResponse, OtpVerify, TokenResponse, UserOut, UserUpdate
from ..security import create_access_token, generate_otp, get_current_user, hash_otp, otp_matches

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger(__name__)


@router.post("/otp/request", response_model=OtpRequestResponse)
def request_otp(body: OtpRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    # Only the latest OTP for a number is valid.
    db.execute(update(OtpCode).where(OtpCode.phone == body.phone, OtpCode.consumed.is_(False)).values(consumed=True))
    otp = generate_otp()
    db.add(
        OtpCode(
            phone=body.phone,
            code_hash=hash_otp(body.phone, otp),
            expires_at=utcnow() + timedelta(minutes=settings.otp_expire_minutes),
        )
    )
    db.commit()

    if settings.dev_mode:
        log.info("Dev OTP for %s: %s", body.phone, otp)
    # TODO: send the OTP by SMS (e.g. MSG91, Twilio) when dev_mode is off.
    return OtpRequestResponse(
        message=f"OTP sent to +91 {body.phone}",
        expires_in_seconds=settings.otp_expire_minutes * 60,
        dev_otp=otp if settings.dev_mode else None,
    )


@router.post("/otp/verify", response_model=TokenResponse)
def verify_otp(body: OtpVerify, db: Session = Depends(get_db)):
    settings = get_settings()
    record = db.scalars(
        select(OtpCode)
        .where(OtpCode.phone == body.phone, OtpCode.consumed.is_(False))
        .order_by(OtpCode.id.desc())
        .limit(1)
    ).first()
    if record is None or record.expires_at < utcnow():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "OTP expired, please request a new one")
    if record.attempts >= settings.otp_max_attempts:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, please request a new OTP")
    if not otp_matches(body.phone, body.otp, record.code_hash):
        record.attempts += 1
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Incorrect OTP")

    record.consumed = True
    user = db.scalars(select(User).where(User.phone == body.phone)).first()
    if user is None:
        user = User(phone=body.phone)
        db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(body: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user
