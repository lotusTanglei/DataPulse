from pathlib import Path
from typing import NoReturn

from fastapi import APIRouter, Depends, Request, Response, UploadFile
from fastapi.responses import FileResponse

from datapulse.auth.dependencies import require_admin, require_csrf
from datapulse.errors import DataPulseError
from datapulse.screen.assets import (
    MAX_ASSET_BYTES,
    AssetInUse,
    AssetInvalid,
    AssetNotFound,
    AssetTooLarge,
    ScreenAssetResponse,
)

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
            message="The screen asset exceeds the 5 MiB limit.",
            status_code=413,
        )
    elif isinstance(error, AssetInvalid):
        translated = DataPulseError(
            code=error.code,
            message="The screen asset is invalid or unsupported.",
            status_code=422,
        )
    elif isinstance(error, AssetInUse):
        translated = DataPulseError(
            code=error.code,
            message="The screen asset is referenced by a screen.",
            status_code=409,
        )
    else:
        raise error
    raise translated from error


@router.post("", status_code=201, dependencies=[Depends(require_csrf)])
async def upload_asset(file: UploadFile, request: Request) -> ScreenAssetResponse:
    try:
        content = await file.read(MAX_ASSET_BYTES + 1)
        asset = await request.app.state.asset_service.upload(
            filename=file.filename or "",
            content_type=file.content_type or "application/octet-stream",
            content=content,
        )
        return ScreenAssetResponse.from_stored(asset)
    except (AssetInvalid, AssetTooLarge) as error:
        _raise_asset_error(error)
    finally:
        await file.close()


@router.get("/{asset_id}")
async def get_asset(asset_id: str, request: Request) -> FileResponse:
    try:
        asset = await request.app.state.asset_service.get(asset_id)
    except AssetNotFound as error:
        _raise_asset_error(error)
    filename = Path(asset.storage_path).name
    return FileResponse(
        asset.storage_path,
        media_type=asset.mime_type,
        headers={
            "Cache-Control": "private, max-age=31536000, immutable",
            "Content-Disposition": f'inline; filename="{filename}"',
            "ETag": f'"{asset.sha256}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{asset_id}", status_code=204, dependencies=[Depends(require_csrf)])
async def delete_asset(asset_id: str, request: Request) -> Response:
    try:
        await request.app.state.asset_service.delete(asset_id)
    except (AssetNotFound, AssetInUse) as error:
        _raise_asset_error(error)
    return Response(status_code=204)
