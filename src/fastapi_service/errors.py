"""Consistent error responses.

Every error the service returns uses the same envelope::

    {"error": {"code": "not_found", "message": "...", "details": ...}}
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for domain errors that map onto an HTTP response."""

    status_code: int = 400
    code: str = "error"

    def __init__(
        self, message: str, *, code: str | None = None, status_code: int | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    status_code = 404
    code = "not_found"


def _envelope(code: str, message: str, details: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


async def app_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Render an :class:`AppError` using the shared envelope."""
    assert isinstance(exc, AppError)
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(exc.code, exc.message),
    )


async def validation_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Render request-validation failures using the shared envelope."""
    assert isinstance(exc, RequestValidationError)
    details = [
        {"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]} for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=_envelope("validation_error", "Request payload failed validation", details),
    )


def register_error_handlers(app: FastAPI) -> None:
    """Attach the error handlers to ``app``."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
