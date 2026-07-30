from typing import Protocol

from pydantic import ValidationError

from datapulse.contracts.chart import ChartSpec, ChartType
from datapulse.contracts.dashboard import DashboardDocument
from datapulse.dataset.repository import DatasetDefinitionInvalid, DatasetNotFound
from datapulse.screen.assets import AssetNotFound
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
    async def assert_references_exist(self, document: DashboardDocument) -> None: ...


_COMPONENT_VISUALS: dict[str, set[ChartType] | None] = {
    "builtin.text": None,
    "builtin.image": None,
    "builtin.kpi": {ChartType.KPI},
    "builtin.table": {ChartType.TABLE},
    "builtin.progress": {ChartType.PROGRESS, ChartType.GAUGE},
    "builtin.line": {ChartType.LINE, ChartType.AREA},
    "builtin.bar": {ChartType.BAR},
    "builtin.pie": {ChartType.PIE},
    "builtin.geo_map": {ChartType.MAP},
}


class PublishingService:
    def __init__(
        self,
        *,
        screen_repository: _ScreenRepository,
        dataset_repository: _DatasetRepository,
        asset_service: _AssetService,
    ) -> None:
        self._screen_repository = screen_repository
        self._dataset_repository = dataset_repository
        self._asset_service = asset_service

    async def _validate(self, document: DashboardDocument) -> None:
        dataset_ids: set[str] = set()
        for component in document.components:
            if component.type not in _COMPONENT_VISUALS:
                raise PublishValidationError(f"Unknown component type: {component.type}")
            binding = component.data_binding
            if not binding:
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
            allowed_visuals = _COMPONENT_VISUALS[component.type]
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
        except AssetNotFound as error:
            raise PublishValidationError(f"Referenced asset is unavailable: {error}") from error

    async def publish(
        self,
        screen_id: str,
        expected_revision: int,
    ) -> ScreenResponse:
        screen = await self._screen_repository.get(screen_id)
        if screen.draft_revision != expected_revision:
            raise ScreenRevisionConflict(screen_id)
        await self._validate(screen.draft_document)
        return await self._screen_repository.publish(
            screen_id,
            document=screen.draft_document,
            expected_revision=expected_revision,
        )


__all__ = ["PublishValidationError", "PublishingService"]
