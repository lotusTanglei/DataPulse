from datetime import timedelta

import pytest

from datapulse.contracts.dashboard import DashboardDocument, DashboardParameter
from datapulse.contracts.dataset import DataType
from datapulse.embedding.repository import EmbedAccessRepository
from datapulse.embedding.service import (
    EmbedApiKeyDenied,
    EmbedParameterDenied,
    EmbedService,
)
from datapulse.embedding.tokens import EmbedTicketCodec
from datapulse.screen.repository import ScreenRepository

pytestmark = pytest.mark.anyio


def parameterized_document() -> DashboardDocument:
    return DashboardDocument(
        canvas={"width": 1920, "height": 1080},
        parameters=(
            DashboardParameter(
                id="region",
                name="region",
                data_type=DataType.STRING,
                default="east",
                mutable=True,
                allowed_values=("east", "west"),
            ),
            DashboardParameter(
                id="year",
                name="year",
                data_type=DataType.INTEGER,
                default=2026,
                mutable=False,
            ),
        ),
    )


async def published_screen(screen_repository: ScreenRepository) -> str:
    created = await screen_repository.create(
        "Operations",
        parameterized_document(),
    )
    await screen_repository.publish(
        created.id,
        document=created.draft_document,
        expected_revision=0,
    )
    return created.id


async def test_api_key_rotation_and_ticket_parameter_authorization(
    screen_repository: ScreenRepository,
    metadata_session_factory,
) -> None:
    screen_id = await published_screen(screen_repository)
    repository = EmbedAccessRepository(metadata_session_factory)
    keys = iter(("first-host-key", "second-host-key"))
    service = EmbedService(
        repository=repository,
        screen_repository=screen_repository,
        codec=EmbedTicketCodec(signing_key=b"e" * 32),
        key_factory=lambda: next(keys),
    )

    first = await service.rotate_api_key()
    stored = await repository.get()
    assert first.plaintext not in repr(stored)
    ticket = await service.issue_ticket(
        api_key=first.plaintext,
        screen_id=screen_id,
        allowed_origin="https://host.example.com",
        parameters={"region": "west"},
        mutable_parameters=("region",),
        lifetime=timedelta(hours=1),
    )
    claims = await service.authorize(ticket, screen_id=screen_id)
    assert claims.parameters == {"region": "west", "year": 2026}
    assert service.resolve_parameters(claims, {"region": "east"}) == {
        "region": "east",
        "year": 2026,
    }

    with pytest.raises(EmbedParameterDenied):
        service.resolve_parameters(claims, {"year": 2027})

    second = await service.rotate_api_key()
    assert second.key_version == 2
    with pytest.raises(EmbedApiKeyDenied):
        await service.issue_ticket(
            api_key=first.plaintext,
            screen_id=screen_id,
            allowed_origin="https://host.example.com",
            parameters={},
            mutable_parameters=(),
            lifetime=timedelta(hours=1),
        )


async def test_ticket_rejects_undeclared_or_immutable_parameters(
    screen_repository: ScreenRepository,
    metadata_session_factory,
) -> None:
    screen_id = await published_screen(screen_repository)
    service = EmbedService(
        repository=EmbedAccessRepository(metadata_session_factory),
        screen_repository=screen_repository,
        codec=EmbedTicketCodec(signing_key=b"e" * 32),
        key_factory=lambda: "host-key",
    )
    api_key = (await service.rotate_api_key()).plaintext

    with pytest.raises(EmbedParameterDenied):
        await service.issue_ticket(
            api_key=api_key,
            screen_id=screen_id,
            allowed_origin="https://host.example.com",
            parameters={"unknown": "value"},
            mutable_parameters=(),
            lifetime=timedelta(hours=1),
        )

    with pytest.raises(EmbedParameterDenied):
        await service.issue_ticket(
            api_key=api_key,
            screen_id=screen_id,
            allowed_origin="https://host.example.com",
            parameters={},
            mutable_parameters=("year",),
            lifetime=timedelta(hours=1),
        )
