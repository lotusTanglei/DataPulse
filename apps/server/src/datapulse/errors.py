import json
import logging
import re
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime
from time import monotonic
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

_request_id_pattern = re.compile(r"[A-Za-z0-9._:-]{1,128}")
request_logger = logging.getLogger("datapulse.requests")


def install_request_logging() -> None:
    request_logger.disabled = False
    if not request_logger.handlers:
        request_logger.addHandler(logging.StreamHandler())
    request_logger.setLevel(logging.INFO)
    request_logger.propagate = False


class DataPulseError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        field_errors: Sequence[dict[str, str]] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.field_errors = tuple(field_errors)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid4()))


def _error_response(
    request: Request,
    *,
    code: str,
    message: str,
    status_code: int,
    field_errors: Sequence[dict[str, str]] = (),
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": _request_id(request),
                "field_errors": list(field_errors),
            }
        },
    )


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    supplied = request.headers.get("X-Request-ID", "")
    request_id = supplied if _request_id_pattern.fullmatch(supplied) else str(uuid4())
    request.state.request_id = request_id
    started = monotonic()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        # Only route templates and fixed fields are recorded. Raw paths, query strings,
        # bodies, exception messages and authorization headers can contain credentials.
        route = getattr(request.scope.get("route"), "path", "unmatched")
        request_logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "time": datetime.now(UTC).isoformat(),
                    "request_id": request_id,
                    "method": request.method,
                    "route": route,
                    "status": status,
                    "duration_ms": round((monotonic() - started) * 1000, 2),
                },
                separators=(",", ":"),
            )
        )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DataPulseError)
    async def handle_datapulse_error(request: Request, error: DataPulseError) -> JSONResponse:
        return _error_response(
            request,
            code=error.code,
            message=error.message,
            status_code=error.status_code,
            field_errors=error.field_errors,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        field_errors: list[dict[str, str]] = []
        for detail in error.errors():
            location = ".".join(str(part) for part in detail["loc"] if part != "body")
            field_errors.append(
                {
                    "field": location,
                    "message": str(detail["msg"]),
                }
            )
        return _error_response(
            request,
            code="REQUEST_VALIDATION_ERROR",
            message="The request is invalid.",
            status_code=422,
            field_errors=field_errors,
        )
