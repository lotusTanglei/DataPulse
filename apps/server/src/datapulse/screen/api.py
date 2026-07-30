from typing import NoReturn

from fastapi import APIRouter, Depends, Request, Response

from datapulse.auth.dependencies import require_admin, require_csrf
from datapulse.errors import DataPulseError
from datapulse.screen.models import (
    ScreenCreate,
    ScreenDraftUpdate,
    ScreenPublish,
    ScreenResponse,
    ScreenSummary,
)
from datapulse.screen.publishing import PublishValidationError
from datapulse.screen.repository import (
    ScreenDocumentInvalid,
    ScreenNameConflict,
    ScreenNotFound,
    ScreenRevisionConflict,
)

router = APIRouter(
    prefix="/api/admin/screens",
    tags=["screens"],
    dependencies=[Depends(require_admin)],
)


def _raise_screen_error(error: Exception) -> NoReturn:
    if isinstance(error, ScreenNotFound):
        translated = DataPulseError(
            code="SCREEN_NOT_FOUND",
            message="The screen does not exist.",
            status_code=404,
        )
    elif isinstance(error, ScreenNameConflict):
        translated = DataPulseError(
            code="SCREEN_NAME_CONFLICT",
            message="A screen with this name already exists.",
            status_code=409,
        )
    elif isinstance(error, ScreenRevisionConflict):
        translated = DataPulseError(
            code="SCREEN_REVISION_CONFLICT",
            message="The screen draft has changed. Reload it before saving again.",
            status_code=409,
        )
    elif isinstance(error, ScreenDocumentInvalid):
        translated = DataPulseError(
            code=error.code,
            message="The screen document is invalid.",
            status_code=422,
        )
    elif isinstance(error, PublishValidationError):
        translated = DataPulseError(
            code=error.code,
            message="The screen cannot be published until its references are valid.",
            status_code=422,
        )
    else:
        raise error
    raise translated from error


@router.get("")
async def list_screens(request: Request) -> tuple[ScreenSummary, ...]:
    try:
        return await request.app.state.screen_service.list()
    except ScreenDocumentInvalid as error:
        _raise_screen_error(error)


@router.post("", status_code=201, dependencies=[Depends(require_csrf)])
async def create_screen(payload: ScreenCreate, request: Request) -> ScreenResponse:
    try:
        return await request.app.state.screen_service.create(payload)
    except ScreenNameConflict as error:
        _raise_screen_error(error)


@router.get("/{screen_id}")
async def get_screen(screen_id: str, request: Request) -> ScreenResponse:
    try:
        return await request.app.state.screen_service.get(screen_id)
    except (ScreenNotFound, ScreenDocumentInvalid) as error:
        _raise_screen_error(error)


@router.patch("/{screen_id}", dependencies=[Depends(require_csrf)])
async def update_screen(
    screen_id: str,
    payload: ScreenDraftUpdate,
    request: Request,
) -> ScreenResponse:
    try:
        return await request.app.state.screen_service.save_draft(screen_id, payload)
    except (
        ScreenNotFound,
        ScreenNameConflict,
        ScreenRevisionConflict,
        ScreenDocumentInvalid,
    ) as error:
        _raise_screen_error(error)


@router.post(
    "/{screen_id}/copy",
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
async def copy_screen(screen_id: str, request: Request) -> ScreenResponse:
    try:
        return await request.app.state.screen_service.copy(screen_id)
    except (ScreenNotFound, ScreenNameConflict, ScreenDocumentInvalid) as error:
        _raise_screen_error(error)


@router.post("/{screen_id}/publish", dependencies=[Depends(require_csrf)])
async def publish_screen(
    screen_id: str,
    payload: ScreenPublish,
    request: Request,
) -> ScreenResponse:
    try:
        return await request.app.state.publishing_service.publish(
            screen_id,
            expected_revision=payload.expected_revision,
        )
    except (
        ScreenNotFound,
        ScreenRevisionConflict,
        ScreenDocumentInvalid,
        PublishValidationError,
    ) as error:
        _raise_screen_error(error)


@router.delete("/{screen_id}", status_code=204, dependencies=[Depends(require_csrf)])
async def delete_screen(screen_id: str, request: Request) -> Response:
    try:
        await request.app.state.screen_service.delete(screen_id)
    except ScreenNotFound as error:
        _raise_screen_error(error)
    return Response(status_code=204)
