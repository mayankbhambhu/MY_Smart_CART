"""Admin tasks from the command line.

    python -m app.manage set-role 98XXXXXXXX staff --store sector-29
    python -m app.manage set-role 98XXXXXXXX admin
    python -m app.manage set-role 98XXXXXXXX customer

Point DATABASE_URL at the hosted database (e.g. Render's external URL) to change it remotely."""

import argparse
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import normalize_phone
from app.models import Store, User, UserRole
from app.seed import init_db


def set_role(phone_raw: str, role: str, store_slug: str | None) -> str:
    phone = normalize_phone(phone_raw)
    if phone is None:
        raise SystemExit(f"Not a valid Indian mobile number: {phone_raw}")
    if role == UserRole.STAFF and not store_slug:
        raise SystemExit("Staff accounts need --store <slug> (e.g. sector-29)")
    init_db(seed=False)
    with SessionLocal() as db:
        store = None
        if store_slug:
            store = db.scalars(select(Store).where(Store.slug == store_slug)).first()
            if store is None:
                slugs = ", ".join(db.scalars(select(Store.slug)))
                raise SystemExit(f"No store '{store_slug}'. Stores: {slugs}")
        user = db.scalars(select(User).where(User.phone == phone)).first()
        if user is None:
            user = User(phone=phone)
            db.add(user)
        user.role = role
        user.store_id = store.id if store and role == UserRole.STAFF else None
        db.commit()
        where = f" at {store.name}" if user.store_id else ""
        return f"{phone} is now {role}{where}. They log in with an SMS code as usual."


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.manage", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    role = commands.add_parser("set-role", help="make a phone number a customer, store staff or admin")
    role.add_argument("phone")
    role.add_argument("role", choices=[r.value for r in UserRole])
    role.add_argument("--store", help="store slug for staff, e.g. sector-29")
    args = parser.parse_args(argv)
    if args.command == "set-role":
        print(set_role(args.phone, args.role, args.store))


if __name__ == "__main__":
    main(sys.argv[1:])
