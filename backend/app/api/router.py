from fastapi import APIRouter

from app.api.routes import addresses, auth, cart, catalog, instore, orders, staff, stores

api_router = APIRouter()


@api_router.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


for module in (auth, catalog, stores, cart, addresses, orders, instore, staff):
    api_router.include_router(module.router)
