from dataclasses import dataclass, field
from contextlib import nullcontext

import pytest

from datapulse.contracts.dashboard import ComponentInstance, DashboardDocument, Frame
from datapulse.dataset.repository import DatasetNotFound
from datapulse.screen.assets import AssetNotFound
from datapulse.screen.publishing import PublishingService, PublishValidationError
from datapulse.screen.repository import ScreenRepository, ScreenRevisionConflict

pytestmark = pytest.mark.anyio


def document_with_component(
    *,
    component_type: str = "builtin.text",
    props: dict[str, object] | None = None,
    data_binding: dict[str, object] | None = None,
) -> DashboardDocument:
    return DashboardDocument(
        canvas={"width": 1920, "height": 1080},
        components=(
            ComponentInstance(
                id="component-1",
                type=component_type,
                frame=Frame(x=40, y=40, width=320, height=120),
                props=props or {"text": "线上版本"},
                data_binding=data_binding or {},
            ),
        ),
    )


@dataclass
class DatasetLookup:
    existing_ids: set[str] = field(default_factory=set)

    async def get(self, dataset_id: str) -> object:
        if dataset_id not in self.existing_ids:
            raise DatasetNotFound(dataset_id)
        return object()


@dataclass
class AssetLookup:
    existing_ids: set[str] = field(default_factory=set)

    def publication_guard(self):
        return nullcontext()

    async def assert_references_exist(self, document: DashboardDocument) -> None:
        referenced = {
            str(component.props["asset_id"])
            for component in document.components
            if isinstance(component.props.get("asset_id"), str) and component.props["asset_id"]
        }
        missing = referenced - self.existing_ids
        if missing:
            raise AssetNotFound(sorted(missing)[0])


def publishing_service(
    screen_repository: ScreenRepository,
    *,
    datasets: set[str] | None = None,
    assets: set[str] | None = None,
) -> PublishingService:
    return PublishingService(
        screen_repository=screen_repository,
        dataset_repository=DatasetLookup(datasets or set()),
        asset_service=AssetLookup(assets or set()),
    )


async def test_publish_atomically_copies_the_current_draft(
    screen_repository: ScreenRepository,
) -> None:
    created = await screen_repository.create(
        "Operations",
        document_with_component(),
    )

    published = await publishing_service(screen_repository).publish(
        created.id,
        expected_revision=0,
    )

    assert published.published_document == created.draft_document
    assert published.published_at is not None
    assert (await screen_repository.get(created.id)).published_document == (created.draft_document)


async def test_failed_validation_preserves_previous_snapshot(
    screen_repository: ScreenRepository,
) -> None:
    created = await screen_repository.create(
        "Operations",
        document_with_component(),
    )
    service = publishing_service(screen_repository)
    before = await service.publish(created.id, expected_revision=0)
    invalid_draft = document_with_component(
        component_type="builtin.image",
        props={"asset_id": "missing-asset"},
    )
    await screen_repository.save_draft(
        created.id,
        document=invalid_draft,
        expected_revision=0,
    )

    with pytest.raises(PublishValidationError):
        await service.publish(created.id, expected_revision=1)

    after = await screen_repository.get(created.id)
    assert after.published_document == before.published_document
    assert after.published_at == before.published_at


async def test_publish_rejects_stale_revision_without_changing_snapshot(
    screen_repository: ScreenRepository,
) -> None:
    created = await screen_repository.create(
        "Operations",
        document_with_component(),
    )
    service = publishing_service(screen_repository)
    before = await service.publish(created.id, expected_revision=0)
    await screen_repository.save_draft(
        created.id,
        document=document_with_component(props={"text": "新草稿"}),
        expected_revision=0,
    )

    with pytest.raises(ScreenRevisionConflict):
        await service.publish(created.id, expected_revision=0)

    after = await screen_repository.get(created.id)
    assert after.published_document == before.published_document
    assert after.published_at == before.published_at


async def test_publish_rejects_unknown_component_type(
    screen_repository: ScreenRepository,
) -> None:
    created = await screen_repository.create(
        "Operations",
        document_with_component(component_type="plugin.unknown"),
    )

    with pytest.raises(PublishValidationError, match="component type"):
        await publishing_service(screen_repository).publish(
            created.id,
            expected_revision=0,
        )


async def test_publish_rejects_missing_dataset_reference(
    screen_repository: ScreenRepository,
) -> None:
    created = await screen_repository.create(
        "Operations",
        document_with_component(
            component_type="builtin.line",
            data_binding={
                "chart_spec": {
                    "dataset_id": "missing-dataset",
                    "dimensions": ["month"],
                    "measures": [{"field": "amount", "aggregation": "sum"}],
                    "visual": {"type": "line"},
                }
            },
        ),
    )

    with pytest.raises(PublishValidationError, match="dataset"):
        await publishing_service(screen_repository).publish(
            created.id,
            expected_revision=0,
        )


async def test_publish_accepts_new_components_with_demo_data(
    screen_repository: ScreenRepository,
) -> None:
    created = await screen_repository.create(
        "Operations",
        document_with_component(
            component_type="builtin.radar",
            data_binding={
                "source": "mock",
                "mock_data": {"preset": "radar", "seed": 42, "row_count": 6},
            },
        ),
    )

    published = await publishing_service(screen_repository).publish(
        created.id,
        expected_revision=0,
    )

    assert published.published_document is not None
    assert published.published_document.components[0].type == "builtin.radar"


async def test_publish_rejects_malformed_static_data(
    screen_repository: ScreenRepository,
) -> None:
    created = await screen_repository.create(
        "Operations",
        document_with_component(
            component_type="builtin.table",
            data_binding={
                "source": "static",
                "static_data": {
                    "columns": [{"name": "value", "data_type": "number"}],
                    "rows": [[1, 2]],
                },
            },
        ),
    )

    with pytest.raises(PublishValidationError, match="static data"):
        await publishing_service(screen_repository).publish(
            created.id,
            expected_revision=0,
        )


@pytest.mark.parametrize(
    "mock_data",
    [
        {"preset": "unknown", "seed": 42},
        {"preset": "radar", "series_count": 4},
        {"preset": "radar", "trend": "sideways"},
        {"preset": "radar", "value_min": 90, "value_max": 10},
    ],
)
async def test_publish_rejects_invalid_demo_data_config(
    screen_repository: ScreenRepository,
    mock_data: dict[str, object],
) -> None:
    created = await screen_repository.create(
        "Operations",
        document_with_component(
            component_type="builtin.radar",
            data_binding={"source": "mock", "mock_data": mock_data},
        ),
    )

    with pytest.raises(PublishValidationError, match="demo data"):
        await publishing_service(screen_repository).publish(
            created.id,
            expected_revision=0,
        )


async def test_publish_rejects_nested_static_values(
    screen_repository: ScreenRepository,
) -> None:
    created = await screen_repository.create(
        "Operations",
        document_with_component(
            component_type="builtin.table",
            data_binding={
                "source": "static",
                "static_data": {
                    "columns": [{"name": "value", "data_type": "number"}],
                    "rows": [[[1, 2]]],
                },
            },
        ),
    )

    with pytest.raises(PublishValidationError, match="static data"):
        await publishing_service(screen_repository).publish(
            created.id,
            expected_revision=0,
        )
