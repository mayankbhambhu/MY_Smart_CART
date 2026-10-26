from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """A user-facing error. `message` is safe to show in the UI as-is."""

    def __init__(self, status_code: int, message: str, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.details = details


class NotFound(AppError):
    def __init__(self, what: str = "Resource"):
        super().__init__(404, f"{what} not found")


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    body: dict[str, Any] = {"detail": exc.message}
    if exc.details is not None:
        body["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=body)
