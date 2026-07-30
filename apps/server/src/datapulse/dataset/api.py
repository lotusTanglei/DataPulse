from typing import NoReturn

from fastapi import APIRouter, Depends, Request, Response

from datapulse.auth.dependencies import require_admin, require_csrf
from datapulse.dataset.models import (
    DatasetCreate,
    DatasetPreviewRequest,
    DatasetResponse,
    DatasetUpdate,
)
from datapulse.dataset.repository import (
    DatasetDefinitionInvalid,
    DatasetNameConflict,
    DatasetNotFound,
    DatasetSourceNotFound,
)
from datapulse.datasource.repository import DatasourceNotFound
from datapulse.errors import DataPulseError
from datapulse.query.execution import QueryExecutionError
from datapulse.query.models import QueryResult
from datapulse.query.parameters import ParameterValidationError
from datapulse.query.safety import QueryValidationError

router = APIRouter(
    prefix="/api/admin/datasets",
    tags=["datasets"],
    dependencies=[Depends(require_admin)],
)


def _raise_dataset_error(error: Exception) -> NoReturn:
    if isinstance(error, DatasetNotFound):
        translated = DataPulseError(
            code="DATASET_NOT_FOUND",
            message="The dataset does not exist.",
            status_code=404,
        )
    elif isinstance(error, DatasetNameConflict):
        translated = DataPulseError(
            code="DATASET_NAME_CONFLICT",
            message="A dataset with this name already exists.",
            status_code=409,
        )
    elif isinstance(error, (DatasetSourceNotFound, DatasourceNotFound)):
        translated = DataPulseError(
            code="DATASET_SOURCE_NOT_FOUND",
            message="The dataset datasource does not exist.",
            status_code=404,
        )
    elif isinstance(error, DatasetDefinitionInvalid):
        translated = DataPulseError(
            code="DATASET_DEFINITION_INVALID",
            message="The stored dataset definition is invalid.",
            status_code=500,
        )
    else:
        raise error
    raise translated from error


def _raise_query_error(error: Exception) -> NoReturn:
    if isinstance(error, QueryValidationError):
        translated = DataPulseError(
            code=error.code,
            message="The dataset query is invalid or not read-only.",
            status_code=422,
        )
    elif isinstance(error, ParameterValidationError):
        translated = DataPulseError(
            code=error.code,
            message="The dataset query parameters are invalid.",
            status_code=422,
            field_errors=tuple(
                {
                    "field": item["field"],
                    "message": "The query parameter is invalid.",
                }
                for item in error.field_errors
            ),
        )
    elif isinstance(error, QueryExecutionError):
        translated = DataPulseError(
            code=error.code,
            message="The dataset query could not be executed.",
            status_code=error.status_code,
        )
    else:
        raise error
    raise translated from error


@router.get("")
async def list_datasets(request: Request) -> tuple[DatasetResponse, ...]:
    try:
        return await request.app.state.dataset_service.list()
    except DatasetDefinitionInvalid as error:
        _raise_dataset_error(error)


@router.post("", status_code=201, dependencies=[Depends(require_csrf)])
async def create_dataset(
    payload: DatasetCreate,
    request: Request,
) -> DatasetResponse:
    try:
        return await request.app.state.dataset_service.create(
            payload,
            request_id=request.state.request_id,
        )
    except (
        DatasetDefinitionInvalid,
        DatasetNameConflict,
        DatasetSourceNotFound,
        DatasourceNotFound,
    ) as error:
        _raise_dataset_error(error)
    except (QueryValidationError, ParameterValidationError, QueryExecutionError) as error:
        _raise_query_error(error)


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str, request: Request) -> DatasetResponse:
    try:
        return await request.app.state.dataset_service.get(dataset_id)
    except (DatasetNotFound, DatasetDefinitionInvalid) as error:
        _raise_dataset_error(error)


@router.patch("/{dataset_id}", dependencies=[Depends(require_csrf)])
async def update_dataset(
    dataset_id: str,
    payload: DatasetUpdate,
    request: Request,
) -> DatasetResponse:
    try:
        return await request.app.state.dataset_service.update(
            dataset_id,
            payload,
            request_id=request.state.request_id,
        )
    except (
        DatasetNotFound,
        DatasetDefinitionInvalid,
        DatasetNameConflict,
        DatasetSourceNotFound,
        DatasourceNotFound,
    ) as error:
        _raise_dataset_error(error)
    except (QueryValidationError, ParameterValidationError, QueryExecutionError) as error:
        _raise_query_error(error)


@router.delete("/{dataset_id}", status_code=204, dependencies=[Depends(require_csrf)])
async def delete_dataset(dataset_id: str, request: Request) -> Response:
    try:
        await request.app.state.dataset_service.delete(dataset_id)
    except DatasetNotFound as error:
        _raise_dataset_error(error)
    return Response(status_code=204)


@router.post(
    "/{dataset_id}/preview",
    dependencies=[Depends(require_csrf)],
)
async def preview_dataset(
    dataset_id: str,
    payload: DatasetPreviewRequest,
    request: Request,
) -> QueryResult:
    try:
        return await request.app.state.dataset_service.preview(
            dataset_id,
            payload,
            request_id=request.state.request_id,
        )
    except (
        DatasetNotFound,
        DatasetDefinitionInvalid,
        DatasourceNotFound,
    ) as error:
        _raise_dataset_error(error)
    except (QueryValidationError, ParameterValidationError, QueryExecutionError) as error:
        _raise_query_error(error)
