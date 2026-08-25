import pytest

from datapulse.contracts.dashboard import ComponentInstance, DashboardDocument, Frame
from datapulse.screen.models import ScreenCreate, ScreenDraftUpdate
from datapulse.screen.repository import ScreenRepository, ScreenRevisionConflict
from datapulse.screen.service import ScreenService

pytestmark = pytest.mark.anyio


def document_with_components() -> DashboardDocument:
    return DashboardDocument(
        canvas={"width": 1920, "height": 1080},
        components=(
            ComponentInstance(
                id="text-1",
                type="builtin.text",
                frame=Frame(x=40, y=40, width=320, height=120),
            ),
            ComponentInstance(
                id="line-1",
                type="builtin.line",
                frame=Frame(x=400, y=40, width=640, height=320),
            ),
        ),
    )


async def test_service_creates_default_screen_and_updates_metadata(
    screen_repository: ScreenRepository,
) -> None:
    service = ScreenService(repository=screen_repository)

    created = await service.create(ScreenCreate(name="Operations", description="Live operations"))
    assert created.draft_document.canvas.width == 1920
    assert created.draft_document.canvas.height == 1080

    updated = await service.save_draft(
        created.id,
        ScreenDraftUpdate(name="Operations center", description="Updated"),
    )
    assert updated.name == "Operations center"
    assert updated.description == "Updated"
    assert updated.draft_revision == 0


async def test_service_creates_screen_with_initial_document(
    screen_repository: ScreenRepository,
) -> None:
    service = ScreenService(repository=screen_repository)
    document = document_with_components()

    created = await service.create(ScreenCreate(name="Generated", draft_document=document))

    assert created.draft_document == document
    assert created.draft_revision == 0


async def test_service_saves_draft_with_optimistic_revision(
    screen_repository: ScreenRepository,
) -> None:
    service = ScreenService(repository=screen_repository)
    created = await service.create(ScreenCreate(name="Operations"))

    saved = await service.save_draft(
        created.id,
        ScreenDraftUpdate(
            draft_document=document_with_components(),
            expected_revision=0,
        ),
    )
    assert saved.draft_revision == 1

    with pytest.raises(ScreenRevisionConflict):
        await service.save_draft(
            created.id,
            ScreenDraftUpdate(
                draft_document=document_with_components(),
                expected_revision=0,
            ),
        )


async def test_stale_draft_does_not_apply_metadata_changes(
    screen_repository: ScreenRepository,
) -> None:
    service = ScreenService(repository=screen_repository)
    created = await service.create(ScreenCreate(name="Operations"))
    await service.save_draft(
        created.id,
        ScreenDraftUpdate(
            draft_document=document_with_components(),
            expected_revision=0,
        ),
    )

    with pytest.raises(ScreenRevisionConflict):
        await service.save_draft(
            created.id,
            ScreenDraftUpdate(
                name="Leaked rename",
                draft_document=document_with_components(),
                expected_revision=0,
            ),
        )

    assert (await service.get(created.id)).name == "Operations"


async def test_copy_rewrites_component_ids_and_uses_conflict_free_names(
    screen_repository: ScreenRepository,
) -> None:
    generated_ids = iter(("copy-1", "component-a", "component-b", "copy-2", "a-2", "b-2"))
    service = ScreenService(
        repository=screen_repository,
        id_factory=lambda: next(generated_ids),
    )
    original = await screen_repository.create(
        "Operations",
        document_with_components(),
        screen_id="original",
    )

    first = await service.copy(original.id)
    second = await service.copy(original.id)

    assert first.id == "copy-1"
    assert first.name == "Operations 副本"
    assert [component.id for component in first.draft_document.components] == [
        "component-a",
        "component-b",
    ]
    assert first.published_document is None
    assert second.id == "copy-2"
    assert second.name == "Operations 副本 2"
    assert [component.id for component in second.draft_document.components] == [
        "a-2",
        "b-2",
    ]
