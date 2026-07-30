from datetime import date, datetime
from typing import Protocol

from pydantic import Field, ValidationError

from datapulse.contracts.chart import ChartSpec, ChartType
from datapulse.contracts.common import ContractModel, JsonValue, NonBlankStr
from datapulse.contracts.dashboard import (
    ComponentInstance,
    DashboardDocument,
    DashboardParameter,
)
from datapulse.dataset.models import DatasetResponse
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


class _ScreenRepository(Protocol):
    async def get(self, screen_id: str) -> ScreenResponse: ...


class _DatasetRepository(Protocol):
    async def get(self, dataset_id: str) -> DatasetResponse: ...


class _DatasourceService(Protocol):
    async def query(
        self,
        datasource_id: str,
        query_request: object,
        *,
        request_id: str,
        dataset_id: str | None = None,
        trigger: str = "debug",
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
        compiler: ChartQueryCompiler | None = None,
    ) -> None:
        self._screen_repository = screen_repository
        self._dataset_repository = dataset_repository
        self._datasource_service = datasource_service
        self._compiler = compiler or ChartQueryCompiler()

    async def _query(
        self,
        *,
        screen: ScreenResponse,
        document: DashboardDocument,
        data: ComponentQueryRequest,
        request_id: str,
        trigger: str,
    ) -> QueryResult:
        del screen
        component = _component(document, data.component_id)
        spec = _chart_spec(component)
        runtime_parameters = resolve_parameters(document, data.parameters)
        dataset = await self._dataset_repository.get(spec.dataset_id)
        request = self._compiler.compile(
            spec=spec,
            dataset=dataset.definition,
            parameters=runtime_parameters,
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
            screen=screen,
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
            screen=screen,
            document=screen.published_document,
            data=data,
            request_id=request_id,
            trigger=trigger,
        )


__all__ = [
    "ComponentBindingInvalid",
    "ComponentQueryRequest",
    "ScreenComponentUnavailable",
    "ScreenNotPublished",
    "ScreenParameterInvalid",
    "ScreenRuntimeService",
    "resolve_parameters",
]
