import math
from contextlib import AbstractAsyncContextManager, nullcontext
from typing import Protocol

from filelock import Timeout
from pydantic import ValidationError

from datapulse.contracts.chart import ChartSpec, ChartType
from datapulse.contracts.dashboard import DashboardDocument
from datapulse.contracts.digital_human import DigitalHumanBinding, DigitalHumanSpec
from datapulse.contracts.speech_template import parse_speech_template
from datapulse.dataset.repository import DatasetDefinitionInvalid, DatasetNotFound
from datapulse.ecosystem.service import EcosystemService
from datapulse.errors import DataPulseError
from datapulse.screen.assets import AssetInvalid, AssetNotFound
from datapulse.screen.media import MediaBusy, MediaUnavailable
from datapulse.screen.models import ScreenResponse
from datapulse.screen.repository import ScreenRevisionConflict


class PublishValidationError(ValueError):
    code = "SCREEN_PUBLISH_INVALID"


class _ScreenRepository(Protocol):
    async def get(self, screen_id: str) -> ScreenResponse: ...

    async def publish(
        self,
        screen_id: str,
        *,
        document: DashboardDocument,
        expected_revision: int,
    ) -> ScreenResponse: ...


class _DatasetRepository(Protocol):
    async def get(self, dataset_id: str) -> object: ...


class _AssetService(Protocol):
    def publication_guard(self) -> AbstractAsyncContextManager: ...

    async def assert_references_exist(self, document: DashboardDocument) -> None: ...


_COMPONENT_VISUALS: dict[str, set[ChartType] | None] = {
    "builtin.digital_human": {ChartType.KPI, ChartType.TABLE},
    "builtin.alert_list": {ChartType.TABLE},
    "builtin.digital_number": {ChartType.KPI},
    "builtin.divider": None,
    "builtin.funnel": {ChartType.FUNNEL},
    "builtin.gauge": {ChartType.GAUGE},
    "builtin.heatmap": {ChartType.HEATMAP},
    "builtin.text": None,
    "builtin.image": None,
    "builtin.kpi": {ChartType.KPI},
    "builtin.table": {ChartType.TABLE},
    "builtin.progress": {ChartType.PROGRESS, ChartType.GAUGE},
    "builtin.line": {ChartType.LINE, ChartType.AREA},
    "builtin.bar": {ChartType.BAR},
    "builtin.pie": {ChartType.PIE},
    "builtin.panel": None,
    "builtin.radar": {ChartType.RADAR},
    "builtin.ranking": {ChartType.TABLE},
    "builtin.scatter": {ChartType.SCATTER},
    "builtin.status_matrix": {ChartType.TABLE},
    "builtin.timeline": {ChartType.TABLE},
    "builtin.geo_map": {ChartType.MAP},
}

_LOCAL_SOURCES = {"dataset", "mock", "static"}
_MOCK_FIELDS = {
    "schema_version",
    "preset",
    "seed",
    "row_count",
    "series_count",
    "category_count",
    "value_min",
    "value_max",
    "trend",
}
_MOCK_PRESETS = {
    "single",
    "series",
    "time_series",
    "table",
    "ranking",
    "alerts",
    "radar",
    "geo",
}
_STATIC_DATA_TYPES = {"boolean", "date", "datetime", "integer", "number", "string"}


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _is_scalar(value: object) -> bool:
    return value is None or isinstance(value, (str, bool)) or _is_number(value)


def _validate_local_binding(component_id: str, binding: dict[str, object]) -> bool:
    source = binding.get("source")
    if source == "mock":
        mock_data = binding.get("mock_data")
        if not isinstance(mock_data, dict):
            raise PublishValidationError(f"Invalid demo data for component: {component_id}")
        if set(mock_data) - _MOCK_FIELDS:
            raise PublishValidationError(f"Invalid demo data for component: {component_id}")
        schema_version = mock_data.get("schema_version")
        if schema_version is not None and schema_version != 1:
            raise PublishValidationError(f"Invalid demo data for component: {component_id}")
        preset = mock_data.get("preset")
        if preset is not None and (not isinstance(preset, str) or preset not in _MOCK_PRESETS):
            raise PublishValidationError(f"Invalid demo data for component: {component_id}")
        seed = mock_data.get("seed")
        if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
            raise PublishValidationError(f"Invalid demo data for component: {component_id}")
        row_count = mock_data.get("row_count")
        if row_count is not None and (
            not isinstance(row_count, int)
            or isinstance(row_count, bool)
            or not 1 <= row_count <= 500
        ):
            raise PublishValidationError(f"Invalid demo data for component: {component_id}")
        for name, minimum, maximum in (
            ("series_count", 1, 3),
            ("category_count", 3, 10),
        ):
            value = mock_data.get(name)
            if value is not None and (
                not isinstance(value, int)
                or isinstance(value, bool)
                or not minimum <= value <= maximum
            ):
                raise PublishValidationError(f"Invalid demo data for component: {component_id}")
        for name in ("value_min", "value_max"):
            value = mock_data.get(name)
            if value is not None and not _is_number(value):
                raise PublishValidationError(f"Invalid demo data for component: {component_id}")
        if mock_data.get("trend") not in {None, "up", "down", "flat"}:
            raise PublishValidationError(f"Invalid demo data for component: {component_id}")
        value_min = mock_data.get("value_min")
        value_max = mock_data.get("value_max")
        if _is_number(value_min) and _is_number(value_max) and value_min > value_max:
            raise PublishValidationError(f"Invalid demo data for component: {component_id}")
        return True
    if source == "static":
        static_data = binding.get("static_data")
        if not isinstance(static_data, dict):
            raise PublishValidationError(f"Invalid static data for component: {component_id}")
        columns = static_data.get("columns")
        rows = static_data.get("rows")
        if (
            not isinstance(columns, list)
            or not isinstance(rows, list)
            or not 1 <= len(columns) <= 20
            or len(rows) > 500
        ):
            raise PublishValidationError(f"Invalid static data for component: {component_id}")
        names = set()
        for column in columns:
            if (
                not isinstance(column, dict)
                or not isinstance(column.get("name"), str)
                or not column["name"].strip()
                or column.get("data_type") not in _STATIC_DATA_TYPES
            ):
                raise PublishValidationError(f"Invalid static data for component: {component_id}")
            names.add(column["name"])
        if len(names) != len(columns) or any(
            not isinstance(row, list)
            or len(row) != len(columns)
            or any(not _is_scalar(value) for value in row)
            for row in rows
        ):
            raise PublishValidationError(f"Invalid static data for component: {component_id}")
        return True
    if source is not None and source not in _LOCAL_SOURCES:
        raise PublishValidationError(f"Invalid data source for component: {component_id}")
    return False


class PublishingService:
    def __init__(
        self,
        *,
        screen_repository: _ScreenRepository,
        dataset_repository: _DatasetRepository,
        asset_service: _AssetService,
        ecosystem_service: EcosystemService | None = None,
    ) -> None:
        self._screen_repository = screen_repository
        self._dataset_repository = dataset_repository
        self._asset_service = asset_service
        self._ecosystem_service = ecosystem_service

    async def _validate(self, document: DashboardDocument) -> None:
        if self._ecosystem_service is not None:
            try:
                self._ecosystem_service.validate_document(document)
            except DataPulseError as error:
                raise PublishValidationError(
                    "Plugin dependencies or properties are invalid."
                ) from error
        dataset_ids: set[str] = set()
        for component in document.components:
            if component.type not in _COMPONENT_VISUALS and (
                self._ecosystem_service is None or component.type.startswith("builtin.")
            ):
                raise PublishValidationError(f"Unknown component type: {component.type}")
            binding = component.data_binding
            if component.type == "builtin.digital_human":
                config = DigitalHumanSpec.model_validate(component.props)
                if config.trigger.kind == "parameter" and config.trigger.parameter not in {
                    parameter.name for parameter in document.parameters
                }:
                    raise PublishValidationError("Unknown speech trigger parameter.")
                if binding.get("source") == "components":
                    references = DigitalHumanBinding.model_validate(binding)
                    components = {item.id: item for item in document.components}
                    names = {item.name for item in references.variables}
                    for variable in references.variables:
                        source = components.get(variable.component_id)
                        if (
                            source is None
                            or source.state.hidden
                            or not source.data_binding
                            or source.type == "builtin.digital_human"
                        ):
                            raise PublishValidationError("Unavailable speech source component.")
                        local = source.data_binding.get("static_data")
                        if isinstance(local, dict) and isinstance(local.get("columns"), list):
                            fields = {
                                column.get("name")
                                for column in local["columns"]
                                if isinstance(column, dict)
                            }
                            if variable.field not in fields:
                                raise PublishValidationError("Unknown speech source field.")
                    if any(
                        token.name not in names
                        for token in parse_speech_template(config.speech_template)
                    ):
                        raise PublishValidationError("Unbound speech template variable.")
                    if config.trigger.variable and config.trigger.variable not in names:
                        raise PublishValidationError("Unbound speech trigger variable.")
                    if any(
                        condition.variable not in names for condition in config.trigger.conditions
                    ):
                        raise PublishValidationError("Unbound speech trigger condition variable.")
                    if any(
                        condition.variable not in names
                        for recording in config.recordings
                        for condition in recording.conditions
                    ):
                        raise PublishValidationError("Unbound speech recording condition variable.")
                    if any(
                        condition.variable not in names
                        for action in config.actions
                        for condition in action.conditions
                    ):
                        raise PublishValidationError(
                            "Unbound digital human action condition variable."
                        )
                    continue
            if not binding:
                continue
            if _validate_local_binding(component.id, binding):
                continue
            payload = binding.get("chart_spec")
            if payload is None:
                raise PublishValidationError(f"Invalid data binding for component: {component.id}")
            try:
                spec = ChartSpec.model_validate(payload)
            except (TypeError, ValueError, ValidationError) as error:
                raise PublishValidationError(
                    f"Invalid data binding for component: {component.id}"
                ) from error
            allowed_visuals = _COMPONENT_VISUALS.get(component.type, set(ChartType))
            if allowed_visuals is None or spec.visual.type not in allowed_visuals:
                raise PublishValidationError(f"Invalid visual type for component: {component.id}")
            dataset_ids.add(spec.dataset_id)

        for dataset_id in sorted(dataset_ids):
            try:
                await self._dataset_repository.get(dataset_id)
            except (DatasetNotFound, DatasetDefinitionInvalid) as error:
                raise PublishValidationError(
                    f"Referenced dataset is unavailable: {dataset_id}"
                ) from error

        try:
            await self._asset_service.assert_references_exist(document)
        except (AssetNotFound, AssetInvalid, MediaBusy, MediaUnavailable) as error:
            raise PublishValidationError(f"Referenced asset is unavailable: {error}") from error

    async def publish(
        self,
        screen_id: str,
        expected_revision: int,
    ) -> ScreenResponse:
        screen = await self._screen_repository.get(screen_id)
        if screen.draft_revision != expected_revision:
            raise ScreenRevisionConflict(screen_id)
        try:
            async with (
                (
                    self._ecosystem_service.publication_guard()
                    if self._ecosystem_service is not None
                    else nullcontext()
                ),
                self._asset_service.publication_guard(),
            ):
                await self._validate(screen.draft_document)
                return await self._screen_repository.publish(
                    screen_id,
                    document=screen.draft_document,
                    expected_revision=expected_revision,
                )
        except Timeout as error:
            raise PublishValidationError(
                "Asset storage is busy. Retry publication shortly."
            ) from error


__all__ = ["PublishValidationError", "PublishingService"]
