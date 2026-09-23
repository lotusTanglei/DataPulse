"""Serve only the exact plugin dependencies of an authorized publication."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from datapulse.display.api import _renew_session
from datapulse.ecosystem.models import CatalogPackage
from datapulse.embedding.api import _authorize, _set_runtime_headers
from datapulse.errors import DataPulseError

router = APIRouter(tags=["published-plugins"])


async def _document(screen_id: str, request: Request, response: Response):
    if request.url.path.startswith("/api/embed/"):
        claims = await _authorize(request, screen_id)
        _set_runtime_headers(response, claims.allowed_origin)
    else:
        await _renew_session(screen_id, request, response)
    screen = await request.app.state.screen_service.get(screen_id)
    if screen.published_document is None:
        raise DataPulseError("SCREEN_NOT_PUBLISHED", "The screen is unavailable.", 409)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return screen.published_document


@router.get("/api/player/screens/{screen_id}/plugins")
@router.get("/api/embed/screens/{screen_id}/plugins")
async def published_plugins(
    screen_id: str, request: Request, response: Response
) -> tuple[CatalogPackage, ...]:
    document = await _document(screen_id, request, response)
    service = request.app.state.ecosystem_service
    return tuple(
        [
            await run_in_threadpool(service.get, "plugin", dependency.id, dependency.version)
            for dependency in document.plugin_dependencies
        ]
    )


@router.get("/api/player/screens/{screen_id}/plugins/{plugin_id}/{version}/files/{file_path:path}")
@router.get("/api/embed/screens/{screen_id}/plugins/{plugin_id}/{version}/files/{file_path:path}")
async def published_plugin_file(
    screen_id: str,
    plugin_id: str,
    version: str,
    file_path: str,
    request: Request,
) -> FileResponse:
    headers = Response()
    document = await _document(screen_id, request, headers)
    path = await run_in_threadpool(
        request.app.state.ecosystem_service.file_path_for_document,
        document,
        plugin_id,
        version,
        file_path,
    )
    response = FileResponse(
        path,
        media_type={
            ".mjs": "text/javascript",
            ".js": "text/javascript",
            ".json": "application/json",
            ".css": "text/css",
        }.get(path.suffix, "application/octet-stream"),
    )
    for name, value in headers.headers.items():
        if name not in {"content-length", "content-type", "set-cookie"}:
            response.headers[name] = value
    if request.url.path.startswith("/api/player/"):
        # Preserve the renewed limited-scope player cookie on streamed responses.
        for value in headers.headers.getlist("set-cookie"):
            response.raw_headers.append((b"set-cookie", value.encode("latin-1")))
    return response
