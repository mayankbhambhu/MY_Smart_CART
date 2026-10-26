import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler
from app.seed import init_db

BACKEND_DIR = Path(__file__).resolve().parent.parent

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def mount_frontend(app: FastAPI, dist: Path) -> None:
    """Serve the built React app (frontend/dist) so one process can run the whole product."""
    index = dist / "index.html"
    if not index.is_file():
        return
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        candidate = (dist / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(dist):
            return FileResponse(candidate)
        return FileResponse(index)  # client-side routes like /orders/12


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate_for_production()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        init_db(seed=settings.auto_seed)
        yield

    app = FastAPI(
        title=f"{settings.app_name} API",
        version="0.1.0",
        description="Quick commerce with delivery, scheduled pickup and in-store shopping.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(api_router, prefix="/api")
    mount_frontend(app, (BACKEND_DIR / settings.frontend_dist).resolve())
    return app


app = create_app()
