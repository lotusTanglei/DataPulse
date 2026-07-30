import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from datapulse.contracts.dashboard import DashboardDocument
from datapulse.display.repository import DisplayAccessRepository
from datapulse.display.service import (
    DisplayAccessDenied,
    DisplayAccessService,
    DisplayScreenUnavailable,
)
from datapulse.display.tokens import DisplaySessionCodec
from datapulse.screen.repository import ScreenRepository

pytestmark = pytest.mark.anyio


def empty_document() -> DashboardDocument:
    return DashboardDocument(canvas={"width": 1920, "height": 1080})


async def published_screen(screen_repository: ScreenRepository) -> str:
    created = await screen_repository.create("Operations", empty_document())
    await screen_repository.publish(
        created.id,
        document=created.draft_document,
        expected_revision=0,
    )
    return created.id


async def test_rotating_key_invalidates_existing_display_session(
    screen_repository: ScreenRepository,
    metadata_session_factory,
) -> None:
    screen_id = await published_screen(screen_repository)
    clock = {"now": datetime(2026, 7, 30, 8, 0, tzinfo=UTC)}
    repository = DisplayAccessRepository(metadata_session_factory)
    keys = iter(("first-display-key", "second-display-key"))
    codec = DisplaySessionCodec(
        signing_key=b"s" * 32,
        now=lambda: clock["now"],
    )
    service = DisplayAccessService(
        repository=repository,
        screen_repository=screen_repository,
        codec=codec,
        key_factory=lambda: next(keys),
    )

    first = await service.generate_key(screen_id)
    stored = await repository.get(screen_id)
    assert stored.key_hash == hashlib.sha256(first.plaintext.encode()).hexdigest()
    assert first.plaintext not in repr(stored)
    session = await service.exchange(screen_id, first.plaintext)

    clock["now"] += timedelta(days=1)
    renewed = await service.authenticate(screen_id, session)
    assert renewed is not False
    claims = codec.verify(renewed)
    assert claims.screen_id == screen_id
    assert claims.key_version == 1
    assert claims.expires_at == clock["now"] + timedelta(days=30)

    second = await service.generate_key(screen_id)
    assert second.key_version == 2
    assert await service.authenticate(screen_id, renewed) is False


async def test_exchange_rejects_wrong_key_and_unpublished_screen(
    screen_repository: ScreenRepository,
    metadata_session_factory,
) -> None:
    repository = DisplayAccessRepository(metadata_session_factory)
    service = DisplayAccessService(
        repository=repository,
        screen_repository=screen_repository,
        codec=DisplaySessionCodec(signing_key=b"s" * 32),
        key_factory=lambda: "display-key",
    )
    published_id = await published_screen(screen_repository)
    await service.generate_key(published_id)

    with pytest.raises(DisplayAccessDenied):
        await service.exchange(published_id, "wrong-key")

    unpublished = await screen_repository.create("Draft", empty_document())
    generated = await service.generate_key(unpublished.id)
    with pytest.raises(DisplayScreenUnavailable):
        await service.exchange(unpublished.id, generated.plaintext)
