import logging
from pathlib import Path
from urllib.parse import parse_qsl, urlencode

from fastapi import Request
from fastapi.responses import FileResponse

from datapulse.embedding.service import EmbedAddressDenied, EmbedOriginDenied
from datapulse.embedding.tokens import EmbedTicketExpired, EmbedTicketInvalid
from datapulse.errors import DataPulseError
from datapulse.screen.access import request_origin_from_headers


def redact_ticket_url(value: str) -> str:
    if "ticket=" not in value:
        return value
    prefix, separator, suffix = value.partition("?")
    if not separator:
        return value
    query, fragment_separator, fragment = suffix.partition("#")
    redacted = [
        (name, "[REDACTED]" if name == "ticket" else item)
        for name, item in parse_qsl(query, keep_blank_values=True)
    ]
    result = f"{prefix}?{urlencode(redacted)}"
    if fragment_separator:
        result = f"{result}#{fragment}"
    return result


class TicketRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_ticket_url(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(
                redact_ticket_url(item) if isinstance(item, str) else item
                for item in record.args
            )
        elif isinstance(record.args, dict):
            record.args = {
                key: redact_ticket_url(item) if isinstance(item, str) else item
                for key, item in record.args.items()
            }
        return True


def install_ticket_redaction_filter() -> None:
    access_logger = logging.getLogger("uvicorn.access")
    if not any(
        isinstance(item, TicketRedactionFilter) for item in access_logger.filters
    ):
        access_logger.addFilter(TicketRedactionFilter())


def _request_origin(request: Request) -> str | None:
    return request_origin_from_headers(
        origin=request.headers.get("origin"),
        referer=request.headers.get("referer"),
    )


async def embed_page_response(
    *,
    request: Request,
    static_root: Path,
    screen_id: str,
    ticket: str,
) -> FileResponse:
    try:
        claims = await request.app.state.embed_service.authorize(
            ticket,
            screen_id=screen_id,
            client_ip=request.client.host if request.client is not None else None,
            request_origin=_request_origin(request),
            enforce_request=True,
        )
        request_origin = _request_origin(request)
    except (EmbedAddressDenied, EmbedOriginDenied) as error:
        raise DataPulseError(
            code=error.code,
            message="The embedding address is not allowed.",
            status_code=403,
        ) from error
    except (EmbedTicketExpired, EmbedTicketInvalid, ValueError) as error:
        raise DataPulseError(
            code="EMBED_TICKET_INVALID",
            message="The embed ticket is invalid.",
            status_code=401,
        ) from error
    if request_origin is not None and request_origin != claims.allowed_origin:
        raise DataPulseError(
            code="EMBED_ORIGIN_DENIED",
            message="The embedding origin is not allowed.",
            status_code=403,
        )
    index = static_root / "index.html"
    if not index.is_file():
        raise DataPulseError(
            code="WEB_APPLICATION_NOT_BUILT",
            message="The web application is not built.",
            status_code=404,
        )
    return FileResponse(
        index,
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": (
                f"frame-ancestors {claims.allowed_origin}"
            ),
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        },
    )


__all__ = [
    "TicketRedactionFilter",
    "embed_page_response",
    "install_ticket_redaction_filter",
    "redact_ticket_url",
]
