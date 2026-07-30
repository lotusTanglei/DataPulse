from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import pytest

from datapulse.auth.bootstrap import BootstrapService
from datapulse.auth.repository import AuthRepository
from datapulse.auth.session import SessionService

pytestmark = pytest.mark.anyio


@dataclass
class MutableClock:
    current: datetime

    def __call__(self) -> datetime:
        return self.current


async def create_admin(repository: AuthRepository, clock: MutableClock) -> str:
    bootstrap = BootstrapService(
        repository,
        clock=clock,
        token_factory=lambda: "setup-code",
    )
    await bootstrap.issue_code()
    admin = await bootstrap.create_admin(
        code="setup-code",
        username="admin",
        password="long-enough-password",
    )
    return admin.id


def deterministic_tokens() -> Callable[[int], bytes]:
    values = iter((b"s" * 32, b"c" * 32, b"x" * 32, b"y" * 32))
    return lambda size: next(values)


async def test_session_creation_persists_hashes_and_authenticates(
    auth_repository: AuthRepository,
) -> None:
    clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
    admin_id = await create_admin(auth_repository, clock)
    service = SessionService(
        auth_repository,
        clock=clock,
        token_factory=deterministic_tokens(),
    )

    created = await service.create(admin_id=admin_id)
    record = await auth_repository.get_session(sha256(created.session_token.encode()).hexdigest())

    assert created.session_token != created.csrf_token
    assert record is not None
    assert record.id != created.session_token
    assert record.csrf_token_hash != created.csrf_token
    assert record.expires_at == clock.current + timedelta(hours=8)
    authenticated = await service.authenticate(created.session_token)
    assert authenticated is not None
    assert authenticated.username == "admin"
    assert await service.verify_csrf(
        created.session_token,
        cookie_token=created.csrf_token,
        header_token=created.csrf_token,
    )


async def test_expired_and_logged_out_sessions_do_not_authenticate(
    auth_repository: AuthRepository,
) -> None:
    clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
    admin_id = await create_admin(auth_repository, clock)
    service = SessionService(
        auth_repository,
        clock=clock,
        token_factory=deterministic_tokens(),
    )
    expired = await service.create(admin_id=admin_id)
    clock.current += timedelta(hours=8, seconds=1)
    assert await service.authenticate(expired.session_token) is None

    current = await service.create(admin_id=admin_id)
    await service.logout(current.session_token)
    assert await service.authenticate(current.session_token) is None


async def test_csrf_requires_matching_cookie_header_and_stored_hash(
    auth_repository: AuthRepository,
) -> None:
    clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
    admin_id = await create_admin(auth_repository, clock)
    service = SessionService(
        auth_repository,
        clock=clock,
        token_factory=deterministic_tokens(),
    )
    created = await service.create(admin_id=admin_id)

    assert not await service.verify_csrf(
        created.session_token,
        cookie_token=created.csrf_token,
        header_token="wrong",
    )
    assert not await service.verify_csrf(
        created.session_token,
        cookie_token="wrong",
        header_token="wrong",
    )


async def test_password_change_can_revoke_every_other_session(
    auth_repository: AuthRepository,
) -> None:
    clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
    admin_id = await create_admin(auth_repository, clock)
    service = SessionService(
        auth_repository,
        clock=clock,
        token_factory=deterministic_tokens(),
    )
    kept = await service.create(admin_id=admin_id)
    revoked = await service.create(admin_id=admin_id)

    await service.revoke_other_sessions(admin_id, kept.session_token)

    assert await service.authenticate(kept.session_token) is not None
    assert await service.authenticate(revoked.session_token) is None
