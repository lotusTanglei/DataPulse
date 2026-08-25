from typing import NoReturn

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import FileResponse

from datapulse.auth.dependencies import require_admin, require_csrf
from datapulse.contracts.common import ContractModel, NonBlankStr
from datapulse.contracts.dashboard import DashboardDocument
from datapulse.display.service import (
    DISPLAY_SESSION_LIFETIME,
    DisplayAccessDenied,
    DisplayAddressDenied,
    DisplayScreenUnavailable,
    DisplaySigningUnavailable,
)
from datapulse.errors import DataPulseError
from datapulse.query.models import QueryResult
from datapulse.screen.access import request_origin_from_headers
from datapulse.screen.assets import AssetNotFound, collect_asset_references
from datapulse.screen.models import ScreenResponse
from datapulse.screen.repository import ScreenNotFound
from datapulse.screen.runtime import ComponentQueryRequest
from datapulse.screen.runtime_api import _raise_runtime_error

DISPLAY_COOKIE = "datapulse_display"


class DisplayKeyResponse(ContractModel):
    screen_id: str
    key_version: int
    key: str


class DisplaySessionRequest(ContractModel):
    key: NonBlankStr


class PlayerScreenResponse(ContractModel):
    id: str
    name: str
    document: DashboardDocument


admin_router = APIRouter(
    prefix="/api/admin/screens",
    tags=["display-access"],
    dependencies=[Depends(require_admin)],
)
player_router = APIRouter(
    prefix="/api/player/screens",
    tags=["screen-player"],
)


def _raise_display_error(error: Exception) -> NoReturn:
    if isinstance(error, ScreenNotFound):
        translated = DataPulseError(
            code="SCREEN_NOT_FOUND",
            message="The screen does not exist.",
            status_code=404,
        )
    elif isinstance(error, DisplayAccessDenied):
        translated = DataPulseError(
            code=error.code,
            message="The display key is invalid.",
            status_code=401,
        )
    elif isinstance(error, DisplayAddressDenied):
        translated = DataPulseError(
            code=error.code,
            message="The display address is not allowed.",
            status_code=403,
        )
    elif isinstance(error, DisplayScreenUnavailable):
        translated = DataPulseError(
            code=error.code,
            message="The screen is not available for playback.",
            status_code=409,
        )
    elif isinstance(error, DisplaySigningUnavailable):
        translated = DataPulseError(
            code=error.code,
            message="Display signing is not configured.",
            status_code=503,
        )
    elif isinstance(error, AssetNotFound):
        translated = DataPulseError(
            code="ASSET_NOT_FOUND",
            message="The screen asset does not exist.",
            status_code=404,
        )
    else:
        raise error
    raise translated from error


def _set_display_cookie(request: Request, response: Response, token: str) -> None:
    response.set_cookie(
        DISPLAY_COOKIE,
        token,
        httponly=True,
        max_age=int(DISPLAY_SESSION_LIFETIME.total_seconds()),
        path="/api/player",
        samesite="lax",
        secure=request.app.state.settings.environment == "production",
    )


async def _renew_session(
    screen_id: str,
    request: Request,
    response: Response,
) -> str:
    origin: str | None
    try:
        origin = request_origin_from_headers(
            origin=request.headers.get("origin"),
            referer=request.headers.get("referer"),
        )
        await request.app.state.display_access_service.authorize_request(
            screen_id,
            origin=origin,
            client_ip=request.client.host if request.client is not None else None,
        )
    except (DisplayAddressDenied, DisplayScreenUnavailable, ScreenNotFound, ValueError) as error:
        if isinstance(error, ValueError) and not isinstance(
            error, (DisplayAddressDenied, DisplayScreenUnavailable)
        ):
            error = DisplayAddressDenied(screen_id)
        _raise_display_error(error)
    token = request.cookies.get(DISPLAY_COOKIE, "")
    renewed = await request.app.state.display_access_service.authenticate(
        screen_id,
        token,
        origin=origin,
        client_ip=request.client.host if request.client is not None else None,
    )
    if renewed is False:
        raise DataPulseError(
            code="DISPLAY_ACCESS_DENIED",
            message="Display access is invalid or expired.",
            status_code=401,
        )
    _set_display_cookie(request, response, renewed)
    return renewed


@admin_router.post(
    "/{screen_id}/display-key",
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
async def generate_display_key(
    screen_id: str,
    request: Request,
) -> DisplayKeyResponse:
    try:
        generated = await request.app.state.display_access_service.generate_key(screen_id)
    except ScreenNotFound as error:
        _raise_display_error(error)
    return DisplayKeyResponse(
        screen_id=generated.screen_id,
        key_version=generated.key_version,
        key=generated.plaintext,
    )


@player_router.post("/{screen_id}/session", status_code=204)
async def exchange_display_key(
    screen_id: str,
    payload: DisplaySessionRequest,
    request: Request,
    response: Response,
) -> None:
    try:
        token = await request.app.state.display_access_service.exchange(
            screen_id,
            payload.key,
            origin=request_origin_from_headers(
                origin=request.headers.get("origin"),
                referer=request.headers.get("referer"),
            ),
            client_ip=request.client.host if request.client is not None else None,
        )
    except (
        DisplayAccessDenied,
        DisplayAddressDenied,
        DisplayScreenUnavailable,
        DisplaySigningUnavailable,
        ScreenNotFound,
        ValueError,
    ) as error:
        if isinstance(error, ValueError) and not isinstance(
            error,
            (DisplayAccessDenied, DisplayAddressDenied),
        ):
            error = DisplayAddressDenied(screen_id)
        _raise_display_error(error)
    _set_display_cookie(request, response, token)


@player_router.get("/{screen_id}")
async def get_player_screen(
    screen_id: str,
    request: Request,
    response: Response,
) -> PlayerScreenResponse:
    await _renew_session(screen_id, request, response)
    try:
        screen: ScreenResponse = await request.app.state.screen_service.get(screen_id)
    except ScreenNotFound as error:
        _raise_display_error(error)
    if screen.published_document is None:
        _raise_display_error(DisplayScreenUnavailable(screen_id))
    return PlayerScreenResponse(
        id=screen.id,
        name=screen.name,
        document=screen.published_document,
    )


@player_router.post("/{screen_id}/query")
async def query_player_component(
    screen_id: str,
    payload: ComponentQueryRequest,
    request: Request,
    response: Response,
) -> QueryResult:
    await _renew_session(screen_id, request, response)
    try:
        return await request.app.state.screen_runtime_service.query_published_component(
            screen_id,
            payload,
            request_id=request.state.request_id,
            trigger="standalone",
        )
    except Exception as error:
        _raise_runtime_error(error)


@player_router.get("/{screen_id}/assets/{asset_id}")
async def get_player_asset(
    screen_id: str,
    asset_id: str,
    request: Request,
    response: Response,
) -> FileResponse:
    renewed = await _renew_session(screen_id, request, response)
    try:
        screen = await request.app.state.screen_service.get(screen_id)
        if screen.published_document is None or asset_id not in collect_asset_references(
            screen.published_document.model_dump(mode="json")
        ):
            raise AssetNotFound(asset_id)
        asset = await request.app.state.asset_service.get(asset_id)
    except (AssetNotFound, ScreenNotFound) as error:
        _raise_display_error(error)
    file_response = FileResponse(
        asset.storage_path,
        media_type=asset.mime_type,
        headers={
            "Cache-Control": "private, max-age=31536000, immutable",
            "ETag": f'"{asset.sha256}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
    _set_display_cookie(request, file_response, renewed)
    return file_response


__all__ = ["DISPLAY_COOKIE", "admin_router", "player_router"]
