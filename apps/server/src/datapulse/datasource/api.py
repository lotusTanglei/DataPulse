from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, Query, Request, Response

from datapulse.auth.dependencies import require_admin, require_csrf
from datapulse.datasource.models import (
    DatasourceCreate,
    DatasourceResponse,
    DatasourceUpdate,
)
from datapulse.datasource.repository import (
    DatasourceInUse,
    DatasourceNameConflict,
    DatasourceNotFound,
)
from datapulse.errors import DataPulseError
from datapulse.query.execution import QueryExecutionError
from datapulse.query.models import QueryRequest, QueryResult
from datapulse.query.parameters import ParameterValidationError
from datapulse.query.safety import QueryValidationError

router = APIRouter(
    prefix="/api/admin/datasources",
    tags=["datasources"],
    dependencies=[Depends(require_admin)],
)


def _raise_repository_error(error: Exception) -> NoReturn:
    if isinstance(error, DatasourceNotFound):
        translated = DataPulseError(
            code="DATASOURCE_NOT_FOUND",
            message="The datasource does not exist.",
            status_code=404,
        )
    elif isinstance(error, DatasourceNameConflict):
        translated = DataPulseError(
            code="DATASOURCE_NAME_CONFLICT",
            message="A datasource with this name already exists.",
            status_code=409,
        )
    elif isinstance(error, DatasourceInUse):
        translated = DataPulseError(
            code="DATASOURCE_IN_USE",
            message="The datasource is in use.",
            status_code=409,
        )
    else:
        raise error
    raise translated from error


def _namespace(value: str | None) -> str | None:
    return value or None


@router.get("")
async def list_datasources(request: Request) -> tuple[DatasourceResponse, ...]:
    return await request.app.state.datasource_service.list()


@router.post("", status_code=201, dependencies=[Depends(require_csrf)])
async def create_datasource(
    payload: DatasourceCreate,
    request: Request,
) -> DatasourceResponse:
    try:
        return await request.app.state.datasource_service.create(payload)
    except (DatasourceNameConflict, DatasourceNotFound, DatasourceInUse) as error:
        _raise_repository_error(error)


@router.get("/{datasource_id}")
async def get_datasource(
    datasource_id: str,
    request: Request,
) -> DatasourceResponse:
    try:
        return await request.app.state.datasource_service.get(datasource_id)
    except DatasourceNotFound as error:
        _raise_repository_error(error)


@router.patch("/{datasource_id}", dependencies=[Depends(require_csrf)])
async def update_datasource(
    datasource_id: str,
    payload: DatasourceUpdate,
    request: Request,
) -> DatasourceResponse:
    try:
        return await request.app.state.datasource_service.update(datasource_id, payload)
    except (DatasourceNameConflict, DatasourceNotFound, DatasourceInUse) as error:
        _raise_repository_error(error)


@router.delete("/{datasource_id}", status_code=204, dependencies=[Depends(require_csrf)])
async def delete_datasource(datasource_id: str, request: Request) -> Response:
    try:
        await request.app.state.datasource_service.delete(datasource_id)
    except (DatasourceNotFound, DatasourceInUse) as error:
        _raise_repository_error(error)
    return Response(status_code=204)


@router.post(
    "/{datasource_id}/test",
    dependencies=[Depends(require_csrf)],
)
async def test_datasource(
    datasource_id: str,
    request: Request,
) -> DatasourceResponse:
    try:
        return await request.app.state.datasource_service.test_connection(datasource_id)
    except DatasourceNotFound as error:
        _raise_repository_error(error)


@router.get("/{datasource_id}/namespaces")
async def list_namespaces(datasource_id: str, request: Request) -> object:
    try:
        return await request.app.state.datasource_service.list_namespaces(
            datasource_id,
            request_id=request.state.request_id,
        )
    except DatasourceNotFound as error:
        _raise_repository_error(error)


@router.get("/{datasource_id}/relations")
async def list_relations(
    datasource_id: str,
    request: Request,
    namespace: Annotated[str | None, Query()] = None,
) -> object:
    try:
        return await request.app.state.datasource_service.list_relations(
            datasource_id,
            _namespace(namespace),
            request_id=request.state.request_id,
        )
    except DatasourceNotFound as error:
        _raise_repository_error(error)


@router.get("/{datasource_id}/relation")
async def describe_relation(
    datasource_id: str,
    request: Request,
    relation: Annotated[str, Query(min_length=1)],
    namespace: Annotated[str | None, Query()] = None,
) -> object:
    try:
        return await request.app.state.datasource_service.describe_relation(
            datasource_id,
            _namespace(namespace),
            relation,
            request_id=request.state.request_id,
        )
    except DatasourceNotFound as error:
        _raise_repository_error(error)


@router.get("/{datasource_id}/relation/preview")
async def preview_relation(
    datasource_id: str,
    request: Request,
    relation: Annotated[str, Query(min_length=1)],
    namespace: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> QueryResult:
    try:
        return await request.app.state.datasource_service.preview_relation(
            datasource_id,
            _namespace(namespace),
            relation,
            limit=limit,
            request_id=request.state.request_id,
        )
    except DatasourceNotFound as error:
        _raise_repository_error(error)


@router.post(
    "/{datasource_id}/query",
    dependencies=[Depends(require_csrf)],
)
async def query_datasource(
    datasource_id: str,
    payload: QueryRequest,
    request: Request,
) -> QueryResult:
    try:
        return await request.app.state.datasource_service.query(
            datasource_id,
            payload,
            request_id=request.state.request_id,
        )
    except DatasourceNotFound as error:
        _raise_repository_error(error)
    except QueryValidationError as error:
        raise DataPulseError(
            code=error.code,
            message="The query is invalid or not read-only.",
            status_code=422,
        ) from error
    except ParameterValidationError as error:
        raise DataPulseError(
            code=error.code,
            message="The query parameters are invalid.",
            status_code=422,
            field_errors=tuple(
                {
                    "field": item["field"],
                    "message": "The query parameter is invalid.",
                }
                for item in error.field_errors
            ),
        ) from error
    except QueryExecutionError as error:
        raise DataPulseError(
            code=error.code,
            message="The query could not be executed.",
            status_code=error.status_code,
        ) from error
