import hashlib
import hmac
import secrets
from datetime import timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db, utcnow
from .models import Role, User

_bearer = HTTPBearer(auto_error=False)


def generate_otp() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def hash_otp(phone: str, otp: str) -> str:
    key = get_settings().jwt_secret.encode()
    return hmac.new(key, f"{phone}:{otp}".encode(), hashlib.sha256).hexdigest()


def otp_matches(phone: str, otp: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(phone, otp), code_hash)


def create_access_token(user: User) -> str:
    settings = get_settings()
    now = utcnow()
    payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _user_from_token(token: str, db: Session) -> User | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
    return db.get(User, user_id)


def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)
) -> User | None:
    if creds is None:
        return None
    return _user_from_token(creds.credentials, db)


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Please log in to continue", headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def require_staff(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.STAFF:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Store staff only")
    return user
