from fastapi import APIRouter, Response
from sqlalchemy import update

from app.api.deps import CurrentUser, DbSession
from app.core.errors import NotFound
from app.models import Address, User
from app.schemas.address import AddressIn, AddressOut

router = APIRouter(prefix="/addresses", tags=["addresses"])


def _own_address(db: DbSession, user: User, address_id: int) -> Address:
    address = db.get(Address, address_id)
    if address is None or address.user_id != user.id:
        raise NotFound("Address")
    return address


def _clear_default(db: DbSession, user: User) -> None:
    db.execute(update(Address).where(Address.user_id == user.id).values(is_default=False))


@router.get("", response_model=list[AddressOut])
def list_addresses(user: CurrentUser):
    return user.addresses


@router.post("", response_model=AddressOut, status_code=201)
def create_address(body: AddressIn, user: CurrentUser, db: DbSession):
    make_default = body.is_default or not user.addresses
    if make_default:
        _clear_default(db, user)
    address = Address(user_id=user.id, **body.model_dump(exclude={"is_default"}), is_default=make_default)
    db.add(address)
    db.commit()
    return address


@router.put("/{address_id}", response_model=AddressOut)
def update_address(address_id: int, body: AddressIn, user: CurrentUser, db: DbSession):
    address = _own_address(db, user, address_id)
    if body.is_default:
        _clear_default(db, user)
    for field, value in body.model_dump().items():
        setattr(address, field, value)
    db.commit()
    db.refresh(address)
    return address


@router.delete("/{address_id}", status_code=204)
def delete_address(address_id: int, user: CurrentUser, db: DbSession):
    address = _own_address(db, user, address_id)
    was_default = address.is_default
    db.delete(address)
    db.flush()
    if was_default:
        remaining = [a for a in user.addresses if a.id != address_id]
        if remaining:
            remaining[0].is_default = True
    db.commit()
    return Response(status_code=204)
