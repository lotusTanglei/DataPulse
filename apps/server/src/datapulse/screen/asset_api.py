from pathlib import Path
from typing import NoReturn

from fastapi import APIRouter, Depends, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse

from datapulse.auth.dependencies import require_admin, require_csrf
from datapulse.contracts.screen_asset import (
    AssetType,
    ScreenAssetPatch,
    ScreenAssetReference,
    ScreenAssetUsage,
)
from datapulse.errors import DataPulseError
from datapulse.screen.assets import (
    AssetInUse,
    AssetInvalid,
    AssetNotFound,
    AssetQuotaExceeded,
    AssetTooLarge,
    ScreenAssetResponse,
)
from datapulse.screen.media import MediaBusy, MediaUnavailable

router = APIRouter(
    prefix="/api/admin/assets",
    tags=["screen-assets"],
    dependencies=[Depends(require_admin)],
)


def _raise_asset_error(error: Exception) -> NoReturn:
    if isinstance(error, AssetNotFound):
        translated = DataPulseError(
            code="ASSET_NOT_FOUND",
            message="The screen asset does not exist.",
            status_code=404,
        )
    elif isinstance(error, AssetTooLarge):
        translated = DataPulseError(
            code=error.code,
            message="The screen asset exceeds its configured upload limit.",
            status_code=413,
        )
    elif isinstance(error, AssetInvalid):
        translated = DataPulseError(
            code=error.code,
            message=str(error),
            status_code=422,
        )
    elif isinstance(error, AssetInUse):
        translated = DataPulseError(
            code=error.code,
            message="The screen asset is referenced by a screen.",
            status_code=409,
        )
    elif isinstance(error, (MediaBusy, MediaUnavailable, AssetQuotaExceeded)):
        translated = DataPulseError(
            code=error.code,
            message=str(error),
            status_code=503 if isinstance(error, MediaUnavailable) else 429,
        )
    else:
        raise error
    raise translated from error


@router.get("")
async def list_assets(
    request: Request,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    search: str = Query(default="", max_length=255),
    asset_type: AssetType | None = None,
    family_id: str | None = Query(default=None, max_length=36),
) -> tuple[ScreenAssetResponse, ...]:
    assets = await request.app.state.asset_service.list(
        offset=offset,
        limit=limit,
        search=search,
        asset_type=asset_type,
        family_id=family_id,
        visible_ids=await request.app.state.identity_service.visible_ids(
            request.state.admin, "asset"
        ),
    )
    return await request.app.state.identity_service.filter_visible(
        request.state.admin, "asset", tuple(asset.public() for asset in assets)
    )


@router.get("/usage")
async def asset_usage(request: Request) -> ScreenAssetUsage:
    return await request.app.state.asset_service.usage(
        visible_ids=await request.app.state.identity_service.visible_ids(
            request.state.admin, "asset"
        )
    )


@router.get("/expiring")
async def expiring_assets(
    request: Request,
    within_days: int = Query(default=30, ge=0, le=3650),
    limit: int = Query(default=100, ge=1, le=100),
) -> tuple[ScreenAssetResponse, ...]:
    assets = await request.app.state.asset_service.expiring(within_days=within_days, limit=limit)
    return await request.app.state.identity_service.filter_visible(
        request.state.admin, "asset", tuple(asset.public() for asset in assets)
    )


@router.post("", status_code=201, dependencies=[Depends(require_csrf)])
async def upload_asset(file: UploadFile, request: Request) -> ScreenAssetResponse:
    try:
        content = await file.read(
            request.app.state.asset_service.upload_limit(file.content_type or "") + 1
        )
        asset = await request.app.state.asset_service.upload(
            filename=file.filename or "",
            content_type=file.content_type or "application/octet-stream",
            content=content,
            uploaded_by=request.state.admin.username,
            reuse_existing=request.state.admin.role == "admin",
        )
        await request.app.state.identity_service.register_owner(
            request.state.admin, "asset", asset.id
        )
        await request.app.state.identity_service.require_access(
            request.state.admin, "asset", asset.id
        )
        return asset.public()
    except (AssetInvalid, AssetTooLarge, MediaBusy, MediaUnavailable, AssetQuotaExceeded) as error:
        _raise_asset_error(error)
    finally:
        await file.close()


@router.post("/{asset_id}/versions", status_code=201, dependencies=[Depends(require_csrf)])
async def replace_asset(asset_id: str, file: UploadFile, request: Request) -> ScreenAssetResponse:
    try:
        content = await file.read(
            request.app.state.asset_service.upload_limit(file.content_type or "") + 1
        )
        asset = await request.app.state.asset_service.upload(
            filename=file.filename or "",
            content_type=file.content_type or "application/octet-stream",
            content=content,
            replaces=asset_id,
            uploaded_by=request.state.admin.username,
            reuse_existing=request.state.admin.role == "admin",
        )
        await request.app.state.identity_service.register_owner(
            request.state.admin, "asset", asset.id
        )
        await request.app.state.identity_service.require_access(
            request.state.admin, "asset", asset.id
        )
        return asset.public()
    except (
        AssetInvalid,
        AssetTooLarge,
        AssetNotFound,
        MediaBusy,
        MediaUnavailable,
        AssetQuotaExceeded,
    ) as error:
        _raise_asset_error(error)
    finally:
        await file.close()


@router.get("/{asset_id}/metadata")
async def asset_metadata(asset_id: str, request: Request) -> ScreenAssetResponse:
    try:
        return (await request.app.state.asset_service.get(asset_id)).public()
    except (AssetNotFound, AssetInvalid) as error:
        _raise_asset_error(error)


@router.patch("/{asset_id}/metadata", dependencies=[Depends(require_csrf)])
async def update_asset(
    asset_id: str, patch: ScreenAssetPatch, request: Request
) -> ScreenAssetResponse:
    try:
        return (await request.app.state.asset_service.update(asset_id, patch)).public()
    except AssetNotFound as error:
        _raise_asset_error(error)


@router.get("/{asset_id}/references")
async def asset_references(asset_id: str, request: Request) -> tuple[ScreenAssetReference, ...]:
    try:
        return await request.app.state.identity_service.filter_visible(
            request.state.admin,
            "screen",
            await request.app.state.asset_service.references(asset_id),
            id_field="screen_id",
        )
    except AssetNotFound as error:
        _raise_asset_error(error)


@router.get("/{asset_id}/thumbnail")
async def asset_thumbnail(asset_id: str, request: Request) -> FileResponse:
    try:
        path = await request.app.state.asset_service.thumbnail(asset_id)
        return FileResponse(
            path,
            media_type="image/png",
            headers={
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except (AssetNotFound, AssetInvalid) as error:
        _raise_asset_error(error)


@router.get("/{asset_id}/preview")
async def asset_preview(
    asset_id: str,
    request: Request,
    normalize_loudness: bool = Query(default=False),
    trim_silence: bool = Query(default=False),
) -> Response:
    try:
        content, media_type = await request.app.state.asset_service.preview(
            asset_id,
            normalize_loudness=normalize_loudness,
            trim_silence=trim_silence,
        )
        return Response(
            content=content,
            media_type=media_type,
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )
    except (AssetNotFound, AssetInvalid, MediaBusy, MediaUnavailable) as error:
        _raise_asset_error(error)


@router.get("/{asset_id}")
async def get_asset(asset_id: str, request: Request) -> FileResponse:
    try:
        asset = await request.app.state.asset_service.get(asset_id)
    except (AssetNotFound, AssetInvalid) as error:
        _raise_asset_error(error)
    filename = Path(asset.storage_path).name
    return FileResponse(
        asset.storage_path,
        media_type=asset.mime_type,
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": f'inline; filename="{filename}"',
            "ETag": f'"{asset.sha256}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{asset_id}", status_code=204, dependencies=[Depends(require_csrf)])
async def delete_asset(asset_id: str, request: Request) -> Response:
    try:
        await request.app.state.asset_service.delete(asset_id)
    except (AssetNotFound, AssetInUse, AssetInvalid, MediaBusy) as error:
        _raise_asset_error(error)
    return Response(status_code=204)
