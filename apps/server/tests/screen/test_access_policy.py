from datetime import timedelta

import pytest
from pydantic import ValidationError

from datapulse.contracts.dashboard import DashboardDocument
from datapulse.display.repository import DisplayAccessRepository
from datapulse.display.service import DisplayAccessService, DisplayAddressDenied
from datapulse.display.tokens import DisplaySessionCodec
from datapulse.embedding.repository import EmbedAccessRepository
from datapulse.embedding.service import (
    EmbedAddressDenied,
    EmbedOriginDenied,
    EmbedService,
)
from datapulse.embedding.tokens import EmbedTicketCodec
from datapulse.screen.access import ScreenAccessPolicy
from datapulse.screen.repository import ScreenRepository

pytestmark = pytest.mark.anyio


def empty_document() -> DashboardDocument:
    return DashboardDocument(canvas={"width": 1920, "height": 1080})


async def published_screen(screen_repository: ScreenRepository) -> str:
    created = await screen_repository.create("Access test", empty_document())
    await screen_repository.publish(
        created.id,
        document=created.draft_document,
        expected_revision=0,
    )
    return created.id


def test_policy_normalizes_exact_origins_and_cidr_rules() -> None:
    policy = ScreenAccessPolicy(
        allowed_origins=("https://Safe.Example.com:443",),
        allowed_ips=("10.0.0.7", "192.0.2.0/24"),
    )

    assert policy.allowed_origins == ("https://safe.example.com",)
    assert policy.allowed_ips == ("10.0.0.7", "192.0.2.0/24")
    assert policy.allows_request(origin="https://safe.example.com", client_ip=None)
    assert policy.allows_request(origin=None, client_ip="192.0.2.33")
    assert not policy.allows_request(origin="https://evil.example.com", client_ip="198.51.100.4")

    with pytest.raises(ValidationError):
        ScreenAccessPolicy(allowed_ips=("not-an-ip",))


async def test_display_access_checks_origin_and_ip_rules(
    screen_repository: ScreenRepository,
    metadata_session_factory,
) -> None:
    screen_id = await published_screen(screen_repository)
    await screen_repository.update_access_policy(
        screen_id,
        access_policy=ScreenAccessPolicy(allowed_ips=("192.0.2.0/24",)),
    )
    service = DisplayAccessService(
        repository=DisplayAccessRepository(metadata_session_factory),
        screen_repository=screen_repository,
        codec=DisplaySessionCodec(signing_key=b"s" * 32),
        key_factory=lambda: "display-key",
    )
    key = await service.generate_key(screen_id)

    with pytest.raises(DisplayAddressDenied):
        await service.exchange(screen_id, key.plaintext, client_ip="198.51.100.9")
    session = await service.exchange(
        screen_id,
        key.plaintext,
        client_ip="192.0.2.22",
    )
    assert await service.authenticate(
        screen_id,
        session,
        client_ip="192.0.2.23",
    )

    await screen_repository.update_access_policy(
        screen_id,
        access_policy=ScreenAccessPolicy(allowed_origins=("https://safe.example.com",)),
    )
    with pytest.raises(DisplayAddressDenied):
        await service.exchange(
            screen_id,
            key.plaintext,
            origin="https://evil.example.com",
            client_ip=None,
        )
    assert await service.exchange(
        screen_id,
        key.plaintext,
        origin="https://safe.example.com",
        client_ip=None,
    )


async def test_embed_ticket_rechecks_screen_policy(
    screen_repository: ScreenRepository,
    metadata_session_factory,
) -> None:
    screen_id = await published_screen(screen_repository)
    await screen_repository.update_access_policy(
        screen_id,
        access_policy=ScreenAccessPolicy(
            allowed_origins=("https://safe.example.com",),
        ),
    )
    service = EmbedService(
        repository=EmbedAccessRepository(metadata_session_factory),
        screen_repository=screen_repository,
        codec=EmbedTicketCodec(signing_key=b"e" * 32),
        key_factory=lambda: "host-key",
    )
    api_key = (await service.rotate_api_key()).plaintext

    with pytest.raises(EmbedOriginDenied):
        await service.issue_ticket(
            api_key=api_key,
            screen_id=screen_id,
            allowed_origin="https://evil.example.com",
            parameters={},
            mutable_parameters=(),
            lifetime=timedelta(hours=1),
        )
    ticket = await service.issue_ticket(
        api_key=api_key,
        screen_id=screen_id,
        allowed_origin="https://safe.example.com",
        parameters={},
        mutable_parameters=(),
        lifetime=timedelta(hours=1),
    )
    assert ticket
    await screen_repository.update_access_policy(
        screen_id,
        access_policy=ScreenAccessPolicy(allowed_ips=("192.0.2.0/24",)),
    )
    ip_ticket = await service.issue_ticket(
        api_key=api_key,
        screen_id=screen_id,
        allowed_origin="https://any.example.com",
        parameters={},
        mutable_parameters=(),
        lifetime=timedelta(hours=1),
    )
    with pytest.raises(EmbedAddressDenied):
        await service.authorize(
            ip_ticket,
            screen_id=screen_id,
            client_ip="198.51.100.4",
        )
    claims = await service.authorize(
        ip_ticket,
        screen_id=screen_id,
        client_ip="192.0.2.4",
    )
    assert claims.allowed_origin == "https://any.example.com"
