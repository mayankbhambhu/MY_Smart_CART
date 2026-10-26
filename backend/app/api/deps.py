from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.models import User

DbSession = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]


def get_optional_user(db: DbSession, credentials: BearerCredentials) -> User | None:
    if credentials is None:
        return None
    user_id = decode_access_token(credentials.credentials)
    return db.get(User, user_id) if user_id is not None else None


def get_current_user(db: DbSession, credentials: BearerCredentials) -> User:
    if credentials is None:
        raise AppError(401, "Please log in to continue")
    user = get_optional_user(db, credentials)
    if user is None:
        raise AppError(401, "Your session has expired. Please log in again.")
    return user


def require_staff(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_staff:
        raise AppError(403, "Store staff only")
    return user


OptionalUser = Annotated[User | None, Depends(get_optional_user)]
CurrentUser = Annotated[User, Depends(get_current_user)]
StaffUser = Annotated[User, Depends(require_staff)]
