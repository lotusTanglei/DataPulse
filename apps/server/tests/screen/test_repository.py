import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from datapulse.contracts.dashboard import ComponentInstance, DashboardDocument, Frame
from datapulse.metadata import ScreenRecord
from datapulse.screen.repository import (
    ScreenDocumentInvalid,
    ScreenNameConflict,
    ScreenNotFound,
    ScreenRepository,
    ScreenRevisionConflict,
)

pytestmark = pytest.mark.anyio


def empty_document() -> DashboardDocument:
    return DashboardDocument(canvas={"width": 1920, "height": 1080})


def document_with_text(text: str) -> DashboardDocument:
    return empty_document().model_copy(
        update={
            "components": (
                ComponentInstance(
                    id="text-1",
                    type="builtin.text",
                    frame=Frame(x=40, y=40, width=320, height=120),
                    props={"text": text},
                ),
            )
        }
    )


async def test_repository_round_trips_screen_crud(
    screen_repository: ScreenRepository,
) -> None:
    created = await screen_repository.create(
        "Operations",
        empty_document(),
        description="Live operations",
    )

    assert created.name == "Operations"
    assert created.description == "Live operations"
    assert created.draft_revision == 0
    assert created.published_document is None
    assert created.published_at is None
    assert created.created_at.tzinfo is not None
    assert created.updated_at.tzinfo is not None
    assert await screen_repository.get(created.id) == created
    assert await screen_repository.list() == (created,)

    renamed = await screen_repository.update_metadata(
        created.id,
        name="Operations center",
        description="Updated",
    )
    assert renamed.name == "Operations center"
    assert renamed.description == "Updated"
    assert renamed.draft_revision == 0

    await screen_repository.delete(created.id)
    with pytest.raises(ScreenNotFound):
        await screen_repository.get(created.id)


async def test_save_draft_requires_matching_revision(
    screen_repository: ScreenRepository,
) -> None:
    created = await screen_repository.create("Operations", empty_document())
    saved = await screen_repository.save_draft(
        created.id,
        document=document_with_text("Live"),
        expected_revision=0,
    )

    assert saved.draft_revision == 1
    assert saved.draft_document.components[0].props["text"] == "Live"

    with pytest.raises(ScreenRevisionConflict):
        await screen_repository.save_draft(
            created.id,
            document=document_with_text("Stale"),
            expected_revision=0,
        )


async def test_repository_maps_unique_name_conflicts(
    screen_repository: ScreenRepository,
) -> None:
    await screen_repository.create("Operations", empty_document())

    with pytest.raises(ScreenNameConflict):
        await screen_repository.create("Operations", empty_document())

    other = await screen_repository.create("Sales", empty_document())
    with pytest.raises(ScreenNameConflict):
        await screen_repository.update_metadata(other.id, name="Operations")


async def test_corrupt_document_maps_to_stable_domain_error(
    screen_repository: ScreenRepository,
    metadata_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    created = await screen_repository.create("Operations", empty_document())
    async with metadata_session_factory.begin() as session:
        await session.execute(
            update(ScreenRecord)
            .where(ScreenRecord.id == created.id)
            .values(draft_document={"schema_version": 999})
        )

    with pytest.raises(ScreenDocumentInvalid) as captured:
        await screen_repository.get(created.id)

    assert captured.value.code == "SCREEN_DOCUMENT_INVALID"
