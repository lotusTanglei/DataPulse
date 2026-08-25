from datetime import timedelta
from typing import NoReturn

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import FileResponse
from pydantic import Field

from datapulse.auth.dependencies import require_admin, require_csrf
from datapulse.contracts.common import ContractModel, JsonValue, NonBlankStr
from datapulse.contracts.dashboard import DashboardDocument
from datapulse.embedding.service import (
    EmbedAddressDenied,
    EmbedApiKeyDenied,
    EmbedOriginDenied,
    EmbedParameterDenied,
    EmbedScreenUnavailable,
    EmbedSigningUnavailable,
)
from datapulse.embedding.tokens import (
    EmbedTicketExpired,
    EmbedTicketInvalid,
    EmbedTicketLifetimeInvalid,
    EmbedTicketOriginInvalid,
)
from datapulse.errors import DataPulseError
from datapulse.query.models import QueryResult
from datapulse.screen.assets import AssetNotFound, collect_asset_references
from datapulse.screen.repository import ScreenNotFound
from datapulse.screen.runtime import ComponentQueryRequest
from datapulse.screen.runtime_api import _raise_runtime_error


class EmbedApiKeyResponse(ContractModel):
    key_version: int
    api_key: str


class EmbedTicketRequest(ContractModel):
    screen_id: NonBlankStr
    allowed_origin: NonBlankStr
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    mutable_parameters: tuple[NonBlankStr, ...] = Field(default_factory=tuple)
    lifetime_seconds: int = Field(default=3600, ge=1, le=8 * 60 * 60)


class EmbedTicketResponse(ContractModel):
    ticket: str
    expires_at: str


class EmbedScreenResponse(ContractModel):
    id: str
    name: str
    document: DashboardDocument
    allowed_origin: str
    parameters: dict[str, JsonValue]
    mutable_parameters: tuple[str, ...]
    expires_at: str


admin_router = APIRouter(
    prefix="/api/admin/embed",
    tags=["embed-access"],
    dependencies=[Depends(require_admin)],
)
router = APIRouter(prefix="/api/embed", tags=["embed-runtime"])


def _bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise DataPulseError(
            code="EMBED_AUTH_REQUIRED",
            message="A Bearer credential is required.",
            status_code=401,
        )
    return token.strip()


def _raise_embed_error(error: Exception) -> NoReturn:
    if isinstance(error, EmbedApiKeyDenied):
        translated = DataPulseError(
            code=error.code,
            message="The host API key is invalid.",
            status_code=401,
        )
    elif isinstance(error, EmbedParameterDenied):
        translated = DataPulseError(
            code=error.code,
            message="The embed parameters are not allowed.",
            status_code=403,
        )
    elif isinstance(error, (EmbedAddressDenied, EmbedOriginDenied)):
        translated = DataPulseError(
            code=error.code,
            message="The embed address is not allowed for this screen.",
            status_code=403,
        )
    elif isinstance(error, (EmbedTicketLifetimeInvalid, EmbedTicketOriginInvalid)):
        translated = DataPulseError(
            code=error.code,
            message="The embed ticket request is invalid.",
            status_code=422,
        )
    elif isinstance(error, (EmbedTicketExpired, EmbedTicketInvalid)):
        translated = DataPulseError(
            code=error.code,
            message="The embed ticket is invalid or expired.",
            status_code=401,
        )
    elif isinstance(error, (EmbedScreenUnavailable, ScreenNotFound)):
        translated = DataPulseError(
            code="EMBED_SCREEN_UNAVAILABLE",
            message="The screen is not available for embedding.",
            status_code=409,
        )
    elif isinstance(error, EmbedSigningUnavailable):
        translated = DataPulseError(
            code=error.code,
            message="Embed signing is not configured.",
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


def _set_runtime_headers(response: Response, allowed_origin: str) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = f"frame-ancestors {allowed_origin}"
    response.headers["X-Content-Type-Options"] = "nosniff"


async def _authorize(request: Request, screen_id: str):
    try:
        return await request.app.state.embed_service.authorize(
            _bearer_token(request),
            screen_id=screen_id,
            client_ip=request.client.host if request.client is not None else None,
        )
    except (
        EmbedTicketExpired,
        EmbedTicketInvalid,
        EmbedScreenUnavailable,
        EmbedSigningUnavailable,
        EmbedAddressDenied,
        EmbedOriginDenied,
    ) as error:
        _raise_embed_error(error)


@admin_router.post(
    "/api-key",
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
async def rotate_embed_api_key(request: Request) -> EmbedApiKeyResponse:
    generated = await request.app.state.embed_service.rotate_api_key()
    return EmbedApiKeyResponse(
        key_version=generated.key_version,
        api_key=generated.plaintext,
    )


@router.post("/tickets", status_code=201)
async def issue_embed_ticket(
    payload: EmbedTicketRequest,
    request: Request,
) -> EmbedTicketResponse:
    try:
        ticket = await request.app.state.embed_service.issue_ticket(
            api_key=_bearer_token(request),
            screen_id=payload.screen_id,
            allowed_origin=payload.allowed_origin,
            parameters=payload.parameters,
            mutable_parameters=payload.mutable_parameters,
            lifetime=timedelta(seconds=payload.lifetime_seconds),
        )
        claims = await request.app.state.embed_service.authorize(
            ticket,
            screen_id=payload.screen_id,
        )
    except (
        EmbedApiKeyDenied,
        EmbedParameterDenied,
        EmbedScreenUnavailable,
        EmbedSigningUnavailable,
        EmbedTicketInvalid,
        EmbedTicketLifetimeInvalid,
        EmbedTicketOriginInvalid,
        EmbedAddressDenied,
        EmbedOriginDenied,
        ScreenNotFound,
    ) as error:
        _raise_embed_error(error)
    return EmbedTicketResponse(
        ticket=ticket,
        expires_at=claims.expires_at.isoformat(),
    )


@router.get("/screens/{screen_id}")
async def get_embed_screen(
    screen_id: str,
    request: Request,
    response: Response,
) -> EmbedScreenResponse:
    claims = await _authorize(request, screen_id)
    try:
        screen = await request.app.state.screen_service.get(screen_id)
    except ScreenNotFound as error:
        _raise_embed_error(error)
    if screen.published_document is None:
        _raise_embed_error(EmbedScreenUnavailable(screen_id))
    _set_runtime_headers(response, claims.allowed_origin)
    return EmbedScreenResponse(
        id=screen.id,
        name=screen.name,
        document=screen.published_document,
        allowed_origin=claims.allowed_origin,
        parameters=claims.parameters,
        mutable_parameters=claims.mutable_parameters,
        expires_at=claims.expires_at.isoformat(),
    )


@router.post("/screens/{screen_id}/query")
async def query_embed_component(
    screen_id: str,
    payload: ComponentQueryRequest,
    request: Request,
    response: Response,
) -> QueryResult:
    claims = await _authorize(request, screen_id)
    try:
        parameters = request.app.state.embed_service.resolve_parameters(
            claims,
            payload.parameters,
        )
        result = await request.app.state.screen_runtime_service.query_published_component(
            screen_id,
            payload.model_copy(update={"parameters": parameters}),
            request_id=request.state.request_id,
            trigger="embed",
        )
    except EmbedParameterDenied as error:
        _raise_embed_error(error)
    except Exception as error:
        _raise_runtime_error(error)
    _set_runtime_headers(response, claims.allowed_origin)
    return result


@router.get("/screens/{screen_id}/assets/{asset_id}")
async def get_embed_asset(
    screen_id: str,
    asset_id: str,
    request: Request,
) -> FileResponse:
    claims = await _authorize(request, screen_id)
    try:
        screen = await request.app.state.screen_service.get(screen_id)
        if screen.published_document is None or asset_id not in collect_asset_references(
            screen.published_document.model_dump(mode="json")
        ):
            raise AssetNotFound(asset_id)
        asset = await request.app.state.asset_service.get(asset_id)
    except (AssetNotFound, ScreenNotFound) as error:
        _raise_embed_error(error)
    return FileResponse(
        asset.storage_path,
        media_type=asset.mime_type,
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": (f"frame-ancestors {claims.allowed_origin}"),
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        },
    )


__all__ = ["admin_router", "router"]
