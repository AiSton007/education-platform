"""Unified error format for every service.

Every error response has the shape::

    {
      "error": {"code": "...", "message": "...", "details": {...}},
      "request_id": "..."
    }
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from pkg.logger import get_logger, get_request_id


class AppError(Exception):
    """Domain-level error with a stable machine-readable code."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class ValidationFailed(AppError):
    def __init__(self, message: str = "Invalid request body", details: Any = None) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class NotFound(AppError):
    def __init__(self, message: str = "Not found", details: Any = None) -> None:
        super().__init__(
            code="NOT_FOUND",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class Unauthorized(AppError):
    def __init__(self, message: str = "Unauthorized", details: Any = None) -> None:
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class Forbidden(AppError):
    def __init__(self, message: str = "Forbidden", details: Any = None) -> None:
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class Conflict(AppError):
    def __init__(self, message: str = "Conflict", details: Any = None) -> None:
        super().__init__(
            code="CONFLICT",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class UpstreamError(AppError):
    def __init__(self, message: str = "Upstream service error", details: Any = None) -> None:
        super().__init__(
            code="UPSTREAM_ERROR",
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


def _payload(code: str, message: str, details: Any) -> dict[str, Any]:
    return {
        "error": {"code": code, "message": message, "details": details},
        "request_id": get_request_id(),
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Wire FastAPI to convert any exception into the unified error envelope."""
    log = get_logger("errors")

    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        log.warning("app_error", code=exc.code, status=exc.status_code, message=exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_payload("VALIDATION_ERROR", "Invalid request body", exc.errors()),
        )

    @app.exception_handler(HTTPException)
    async def _http(_: Request, exc: HTTPException):
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
            500: "INTERNAL_ERROR",
            502: "UPSTREAM_ERROR",
            503: "SERVICE_UNAVAILABLE",
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(
                code_map.get(exc.status_code, "ERROR"),
                str(exc.detail) if exc.detail is not None else "Error",
                None,
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.exception("unhandled_exception", error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_payload("INTERNAL_ERROR", "Internal server error", None),
        )
