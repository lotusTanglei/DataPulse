from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import pytest

from datapulse.auth.bootstrap import (
    BootstrapService,
    BootstrapUnavailable,
    InvalidSetupCode,
)
from datapulse.auth.repository import AuthRepository

pytestmark = pytest.mark.anyio


@dataclass
class MutableClock:
    current: datetime

    def __call__(self) -> datetime:
        return self.current


async def test_issue_code_returns_raw_value_but_persists_only_hash(
    auth_repository: AuthRepository,
) -> None:
    clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
    service = BootstrapService(
        auth_repository,
        clock=clock,
        token_factory=lambda: "setup-code",
    )

    raw_code = await service.issue_code()
    state = await auth_repository.get_system_state()

    assert raw_code == "setup-code"
    assert state.setup_code_hash == sha256(b"setup-code").hexdigest()
    assert state.setup_code_hash != raw_code
    assert state.setup_code_expires_at == clock.current + timedelta(minutes=30)


async def test_setup_code_is_single_use_and_rejects_wrong_value(
    auth_repository: AuthRepository,
) -> None:
    service = BootstrapService(
        auth_repository,
        clock=MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC)),
        token_factory=lambda: "setup-code",
    )
    await service.issue_code()

    assert not await service.consume_code("wrong-code")
    assert await service.consume_code("setup-code")
    assert not await service.consume_code("setup-code")


async def test_setup_code_expires_after_thirty_minutes(
    auth_repository: AuthRepository,
) -> None:
    clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
    service = BootstrapService(
        auth_repository,
        clock=clock,
        token_factory=lambda: "setup-code",
    )
    await service.issue_code()
    clock.current += timedelta(minutes=31)

    assert not await service.consume_code("setup-code")


async def test_restart_replaces_an_unconsumed_setup_code(
    auth_repository: AuthRepository,
) -> None:
    clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
    first = BootstrapService(
        auth_repository,
        clock=clock,
        token_factory=lambda: "first-code",
    )
    second = BootstrapService(
        auth_repository,
        clock=clock,
        token_factory=lambda: "second-code",
    )

    assert await first.issue_code() == "first-code"
    assert await second.issue_code() == "second-code"
    assert not await second.consume_code("first-code")
    assert await second.consume_code("second-code")


async def test_create_admin_consumes_code_and_prevents_another_bootstrap(
    auth_repository: AuthRepository,
) -> None:
    service = BootstrapService(
        auth_repository,
        clock=MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC)),
        token_factory=lambda: "setup-code",
    )
    await service.issue_code()

    admin = await service.create_admin(
        code="setup-code",
        username="admin",
        password="long-enough-password",
    )

    assert admin.username == "admin"
    assert await auth_repository.get_admin_by_username("admin") is not None
    assert not await service.consume_code("setup-code")
    with pytest.raises(BootstrapUnavailable):
        await service.issue_code()


async def test_create_admin_rejects_wrong_setup_code(
    auth_repository: AuthRepository,
) -> None:
    service = BootstrapService(
        auth_repository,
        clock=MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC)),
        token_factory=lambda: "setup-code",
    )
    await service.issue_code()

    with pytest.raises(InvalidSetupCode):
        await service.create_admin(
            code="wrong-code",
            username="admin",
            password="long-enough-password",
        )

    assert await auth_repository.get_admin_by_username("admin") is None
