from datetime import date, datetime
from pathlib import Path
from typing import Protocol

from pydantic import Field, ValidationError

from datapulse.contracts.chart import ChartSpec, ChartType
from datapulse.contracts.common import ContractModel, JsonValue, NonBlankStr
from datapulse.contracts.dashboard import (
    ComponentInstance,
    DashboardDocument,
    DashboardParameter,
)
from datapulse.contracts.dataset import RestQuery
from datapulse.dataset.models import DatasetResponse
from datapulse.filedata.parsers import parse_file
from datapulse.filedata.query import FileDatasetQueryService
from datapulse.query.models import QueryResult
from datapulse.screen.chart_query import ChartQueryCompiler
from datapulse.screen.models import ScreenResponse


class ScreenComponentUnavailable(LookupError):
    code = "SCREEN_COMPONENT_UNAVAILABLE"


class ComponentBindingInvalid(ValueError):
    code = "SCREEN_COMPONENT_BINDING_INVALID"


class ScreenParameterInvalid(ValueError):
    code = "SCREEN_PARAMETER_INVALID"


class ScreenNotPublished(LookupError):
    code = "SCREEN_NOT_PUBLISHED"


class ComponentQueryRequest(ContractModel):
    component_id: NonBlankStr
    parameters: dict[str, JsonValue] = Field(default_factory=dict)


class ScreenDocumentQueryRequest(ComponentQueryRequest):
    document: DashboardDocument


class _ScreenRepository(Protocol):
    async def get(self, screen_id: str) -> ScreenResponse: ...


class _DatasetRepository(Protocol):
    async def get(self, dataset_id: str) -> DatasetResponse: ...


class _FileAssetRepository(Protocol):
    async def get(self, asset_id: str): ...


class _DatasourceService(Protocol):
    async def dialect(self, datasource_id: str) -> str: ...

    async def query(
        self,
        datasource_id: str,
        query_request: object,
        *,
        request_id: str,
        dataset_id: str | None = None,
        trigger: str = "debug",
    ) -> QueryResult: ...

    async def rest_query(
        self,
        datasource_id: str,
        query: RestQuery,
        *,
        parameters: dict[str, JsonValue],
        max_rows: int,
        timeout_seconds: int,
        request_id: str,
    ) -> QueryResult: ...


_COMPONENT_VISUALS = {
    "builtin.bar": {ChartType.BAR},
    "builtin.geo_map": {ChartType.MAP},
    "builtin.kpi": {ChartType.KPI},
    "builtin.line": {ChartType.LINE, ChartType.AREA},
    "builtin.pie": {ChartType.PIE},
    "builtin.progress": {ChartType.PROGRESS, ChartType.GAUGE},
    "builtin.table": {ChartType.TABLE},
}


def _component(document: DashboardDocument, component_id: str) -> ComponentInstance:
    component = next(
        (item for item in document.components if item.id == component_id),
        None,
    )
    if component is None or component.state.hidden:
        raise ScreenComponentUnavailable(component_id)
    return component


def _chart_spec(component: ComponentInstance) -> ChartSpec:
    payload = component.data_binding.get("chart_spec")
    if payload is None:
        raise ComponentBindingInvalid(component.id)
    try:
        spec = ChartSpec.model_validate(payload)
    except (TypeError, ValueError, ValidationError) as error:
        raise ComponentBindingInvalid(component.id) from error
    allowed_visuals = _COMPONENT_VISUALS.get(component.type)
    if allowed_visuals is None or spec.visual.type not in allowed_visuals:
        raise ComponentBindingInvalid(component.id)
    return spec


def _value_matches(parameter: DashboardParameter, value: JsonValue) -> bool:
    if value is None:
        return True
    if parameter.data_type.value == "string":
        return isinstance(value, str)
    if parameter.data_type.value == "boolean":
        return isinstance(value, bool)
    if parameter.data_type.value == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if parameter.data_type.value == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if not isinstance(value, str):
        return False
    try:
        if parameter.data_type.value == "date":
            date.fromisoformat(value)
        else:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def resolve_parameters(
    document: DashboardDocument,
    supplied: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    definitions = {parameter.name: parameter for parameter in document.parameters}
    if not set(supplied) <= set(definitions):
        raise ScreenParameterInvalid("Unknown screen parameter.")
    resolved: dict[str, JsonValue] = {}
    for name, parameter in definitions.items():
        value = supplied.get(name, parameter.default)
        if not _value_matches(parameter, value):
            raise ScreenParameterInvalid(name)
        if parameter.allowed_values and value not in parameter.allowed_values:
            raise ScreenParameterInvalid(name)
        resolved[name] = value
    return resolved


class ScreenRuntimeService:
    def __init__(
        self,
        *,
        screen_repository: _ScreenRepository,
        dataset_repository: _DatasetRepository,
        datasource_service: _DatasourceService,
        file_asset_repository: _FileAssetRepository | None = None,
        file_query_service: FileDatasetQueryService | None = None,
        compiler: ChartQueryCompiler | None = None,
    ) -> None:
        self._screen_repository = screen_repository
        self._dataset_repository = dataset_repository
        self._datasource_service = datasource_service
        self._file_asset_repository = file_asset_repository
        self._file_query_service = file_query_service
        self._compiler = compiler or ChartQueryCompiler()

    async def _query(
        self,
        *,
        document: DashboardDocument,
        data: ComponentQueryRequest,
        request_id: str,
        trigger: str,
    ) -> QueryResult:
        component = _component(document, data.component_id)
        spec = _chart_spec(component)
        runtime_parameters = resolve_parameters(document, data.parameters)
        dataset = await self._dataset_repository.get(spec.dataset_id)
        if dataset.definition.query.kind == "file":
            if self._file_asset_repository is None or self._file_query_service is None:
                raise ComponentBindingInvalid(component.id)
            asset = await self._file_asset_repository.get(dataset.definition.query.asset_id)
            parsed = await parse_file(
                Path(asset.storage_path),
                dataset.definition.query.format,
                sheet_name=dataset.definition.query.sheet_name,
                max_rows=dataset.definition.max_rows,
            )
            return await self._file_query_service.query(
                dataset=dataset.definition,
                chart_spec=spec,
                parameters=runtime_parameters,
                request_id=request_id,
                source_path=parsed.normalized_path,
            )
        if dataset.definition.query.kind == "rest":
            return await self._datasource_service.rest_query(
                dataset.data_source_id,
                dataset.definition.query,
                parameters=runtime_parameters,
                max_rows=dataset.definition.max_rows,
                timeout_seconds=dataset.definition.timeout_seconds,
                request_id=request_id,
            )
        dialect = await self._datasource_service.dialect(dataset.data_source_id)
        request = self._compiler.compile(
            spec=spec,
            dataset=dataset.definition,
            parameters=runtime_parameters,
            dialect=dialect,
        )
        return await self._datasource_service.query(
            dataset.data_source_id,
            request,
            request_id=request_id,
            dataset_id=dataset.id,
            trigger=trigger,
        )

    async def query_draft_component(
        self,
        screen_id: str,
        data: ComponentQueryRequest,
        *,
        request_id: str,
    ) -> QueryResult:
        screen = await self._screen_repository.get(screen_id)
        return await self._query(
            document=screen.draft_document,
            data=data,
            request_id=request_id,
            trigger="screen-draft",
        )

    async def query_published_component(
        self,
        screen_id: str,
        data: ComponentQueryRequest,
        *,
        request_id: str,
        trigger: str,
    ) -> QueryResult:
        screen = await self._screen_repository.get(screen_id)
        if screen.published_document is None:
            raise ScreenNotPublished(screen_id)
        return await self._query(
            document=screen.published_document,
            data=data,
            request_id=request_id,
            trigger=trigger,
        )

    async def query_document_component(
        self,
        data: ScreenDocumentQueryRequest,
        *,
        request_id: str,
    ) -> QueryResult:
        return await self._query(
            document=data.document,
            data=ComponentQueryRequest(
                component_id=data.component_id,
                parameters=data.parameters,
            ),
            request_id=request_id,
            trigger="screen-document-preview",
        )


__all__ = [
    "ComponentBindingInvalid",
    "ComponentQueryRequest",
    "ScreenComponentUnavailable",
    "ScreenDocumentQueryRequest",
    "ScreenNotPublished",
    "ScreenParameterInvalid",
    "ScreenRuntimeService",
    "resolve_parameters",
]
