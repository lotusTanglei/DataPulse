from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile

from datapulse.auth.dependencies import require_admin, require_csrf
from datapulse.contracts.filedata import FileAssetResponse, FilePreviewResponse
from datapulse.errors import DataPulseError
from datapulse.filedata.parsers import FileParseInvalid
from datapulse.filedata.repository import FileAssetNotFound, FileInUse
from datapulse.filedata.storage import FileEmpty, FileTooLarge, FileTypeUnsupported

router = APIRouter(
    prefix="/api/admin/files",
    tags=["files"],
    dependencies=[Depends(require_admin)],
)


def _raise_file_error(error: Exception) -> NoReturn:
    if isinstance(error, FileAssetNotFound):
        translated = DataPulseError(
            code="FILE_NOT_FOUND",
            message="The file asset does not exist.",
            status_code=404,
        )
    elif isinstance(error, FileInUse):
        translated = DataPulseError(
            code="FILE_IN_USE",
            message="The file asset is referenced by a dataset.",
            status_code=409,
        )
    elif isinstance(error, FileTypeUnsupported):
        translated = DataPulseError(
            code="FILE_TYPE_UNSUPPORTED",
            message="The uploaded file format is not supported.",
            status_code=422,
        )
    elif isinstance(error, FileTooLarge):
        translated = DataPulseError(
            code="FILE_TOO_LARGE",
            message="The uploaded file exceeds the size limit.",
            status_code=413,
        )
    elif isinstance(error, FileEmpty):
        translated = DataPulseError(
            code="FILE_EMPTY",
            message="The uploaded file is empty.",
            status_code=422,
        )
    elif isinstance(error, FileParseInvalid):
        translated = DataPulseError(
            code="FILE_PARSE_INVALID",
            message="The uploaded file could not be parsed.",
            status_code=422,
        )
    else:
        raise error
    raise translated from error


@router.get("")
async def list_files(request: Request) -> tuple[FileAssetResponse, ...]:
    try:
        return await request.app.state.identity_service.filter_visible(
            request.state.admin, "file", await request.app.state.file_asset_service.list()
        )
    except FileAssetNotFound as error:
        _raise_file_error(error)


@router.post("", status_code=201, dependencies=[Depends(require_csrf)])
async def upload_file(
    request: Request,
    file: Annotated[UploadFile, File()],
) -> FileAssetResponse:
    try:
        result = await request.app.state.file_asset_service.ingest(
            file,
            request_id=request.state.request_id,
        )
        await request.app.state.identity_service.register_owner(
            request.state.admin, "file", result.id
        )
        return result
    except (
        FileAssetNotFound,
        FileInUse,
        FileTypeUnsupported,
        FileTooLarge,
        FileEmpty,
        FileParseInvalid,
    ) as error:
        _raise_file_error(error)


@router.get("/{asset_id}/preview")
async def preview_file(
    asset_id: str,
    request: Request,
    sheet_name: str | None = None,
) -> FilePreviewResponse:
    try:
        return await request.app.state.file_asset_service.preview(
            asset_id,
            sheet_name=sheet_name,
            request_id=request.state.request_id,
        )
    except (FileAssetNotFound, FileParseInvalid) as error:
        _raise_file_error(error)


@router.delete("/{asset_id}", status_code=204, dependencies=[Depends(require_csrf)])
async def delete_file(asset_id: str, request: Request) -> Response:
    try:
        await request.app.state.file_asset_service.delete(asset_id)
    except (
        FileAssetNotFound,
        FileInUse,
        FileTypeUnsupported,
        FileTooLarge,
        FileEmpty,
        FileParseInvalid,
    ) as error:
        _raise_file_error(error)
    return Response(status_code=204)
