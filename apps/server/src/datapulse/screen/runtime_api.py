from typing import NoReturn

from fastapi import APIRouter, Depends, Request

from datapulse.auth.dependencies import require_admin, require_csrf
from datapulse.dataset.repository import (
    DatasetDefinitionInvalid,
    DatasetNotFound,
)
from datapulse.datasource.repository import DatasourceNotFound
from datapulse.errors import DataPulseError
from datapulse.query.execution import QueryExecutionError
from datapulse.query.models import QueryResult
from datapulse.query.parameters import ParameterValidationError
from datapulse.query.safety import QueryValidationError
from datapulse.screen.chart_query import ChartQueryInvalid
from datapulse.screen.repository import (
    ScreenDocumentInvalid,
    ScreenNotFound,
)
from datapulse.screen.runtime import (
    ComponentBindingInvalid,
    ComponentQueryRequest,
    ScreenComponentUnavailable,
    ScreenDocumentQueryRequest,
    ScreenNotPublished,
    ScreenParameterInvalid,
)

router = APIRouter(
    prefix="/api/admin/screens",
    tags=["screen-runtime"],
    dependencies=[Depends(require_admin)],
)


def _raise_runtime_error(error: Exception) -> NoReturn:
    if isinstance(error, ScreenNotFound):
        translated = DataPulseError(
            code="SCREEN_NOT_FOUND",
            message="The screen does not exist.",
            status_code=404,
        )
    elif isinstance(error, ScreenNotPublished):
        translated = DataPulseError(
            code=error.code,
            message="The screen has not been published.",
            status_code=409,
        )
    elif isinstance(error, ScreenComponentUnavailable):
        translated = DataPulseError(
            code=error.code,
            message="The screen component is unavailable.",
            status_code=422,
        )
    elif isinstance(error, (ComponentBindingInvalid, DatasetNotFound, DatasourceNotFound)):
        translated = DataPulseError(
            code="SCREEN_COMPONENT_BINDING_INVALID",
            message="The screen component data binding is invalid.",
            status_code=422,
        )
    elif isinstance(error, ScreenParameterInvalid):
        translated = DataPulseError(
            code=error.code,
            message="The screen parameters are invalid.",
            status_code=422,
        )
    elif isinstance(error, ChartQueryInvalid):
        translated = DataPulseError(
            code=error.code,
            message="The screen chart query is invalid.",
            status_code=422,
        )
    elif isinstance(error, ScreenDocumentInvalid):
        translated = DataPulseError(
            code=error.code,
            message="The stored screen document is invalid.",
            status_code=422,
        )
    elif isinstance(error, DatasetDefinitionInvalid):
        translated = DataPulseError(
            code=error.code,
            message="The stored dataset definition is invalid.",
            status_code=422,
        )
    elif isinstance(error, QueryValidationError):
        translated = DataPulseError(
            code=error.code,
            message="The component query is invalid.",
            status_code=422,
        )
    elif isinstance(error, ParameterValidationError):
        translated = DataPulseError(
            code=error.code,
            message="The component query parameters are invalid.",
            status_code=422,
        )
    elif isinstance(error, QueryExecutionError):
        translated = DataPulseError(
            code=error.code,
            message="The component query could not be executed.",
            status_code=error.status_code,
        )
    else:
        raise error
    raise translated from error


_RUNTIME_ERRORS = (
    ScreenNotFound,
    ScreenNotPublished,
    ScreenComponentUnavailable,
    ComponentBindingInvalid,
    ScreenParameterInvalid,
    ChartQueryInvalid,
    ScreenDocumentInvalid,
    DatasetNotFound,
    DatasetDefinitionInvalid,
    DatasourceNotFound,
    QueryValidationError,
    ParameterValidationError,
    QueryExecutionError,
)


@router.post("/query-document", dependencies=[Depends(require_csrf)])
async def query_document_component(
    payload: ScreenDocumentQueryRequest,
    request: Request,
) -> QueryResult:
    try:
        return await request.app.state.screen_runtime_service.query_document_component(
            payload,
            request_id=request.state.request_id,
        )
    except _RUNTIME_ERRORS as error:
        _raise_runtime_error(error)


@router.post("/{screen_id}/query", dependencies=[Depends(require_csrf)])
async def query_draft_component(
    screen_id: str,
    payload: ComponentQueryRequest,
    request: Request,
) -> QueryResult:
    try:
        return await request.app.state.screen_runtime_service.query_draft_component(
            screen_id,
            payload,
            request_id=request.state.request_id,
        )
    except _RUNTIME_ERRORS as error:
        _raise_runtime_error(error)
