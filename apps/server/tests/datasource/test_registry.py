from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from datapulse.datasource.engine_manager import EngineManager
from datapulse.datasource.models import ConnectorType
from datapulse.datasource.registry import (
    ConnectorAlreadyRegistered,
    ConnectorNotFound,
    ConnectorRegistry,
)


@dataclass
class StubConnector:
    type: ConnectorType
    dialect: str


@dataclass
class DisposableEngine:
    name: str
    disposed: bool = False

    async def dispose(self) -> None:
        self.disposed = True


def test_registry_resolves_connector_and_rejects_unknown_type() -> None:
    sqlite = StubConnector(ConnectorType.SQLITE, "sqlite")
    registry = ConnectorRegistry([sqlite])

    assert registry.get(ConnectorType.SQLITE) is sqlite
    with pytest.raises(ConnectorNotFound):
        registry.get("oracle")


def test_registry_rejects_duplicate_connector_types() -> None:
    first = StubConnector(ConnectorType.SQLITE, "sqlite")
    second = StubConnector(ConnectorType.SQLITE, "sqlite")

    with pytest.raises(ConnectorAlreadyRegistered):
        ConnectorRegistry([first, second])


@pytest.mark.anyio
async def test_engine_manager_reuses_same_version_and_disposes_replaced_engine() -> None:
    manager = EngineManager()
    updated_at = datetime(2026, 7, 30, 8, 0, tzinfo=UTC)
    first = DisposableEngine("first")
    replacement = DisposableEngine("replacement")

    assert await manager.get("source-1", updated_at, lambda: first) is first
    assert await manager.get("source-1", updated_at, lambda: replacement) is first
    assert replacement.disposed is False

    resolved = await manager.get(
        "source-1",
        updated_at + timedelta(seconds=1),
        lambda: replacement,
    )

    assert resolved is replacement
    assert first.disposed is True


@pytest.mark.anyio
async def test_engine_manager_disposes_one_source_and_all_on_shutdown() -> None:
    manager = EngineManager()
    updated_at = datetime(2026, 7, 30, 8, 0, tzinfo=UTC)
    first = DisposableEngine("first")
    second = DisposableEngine("second")
    await manager.get("source-1", updated_at, lambda: first)
    await manager.get("source-2", updated_at, lambda: second)

    await manager.dispose("source-1")

    assert first.disposed is True
    assert second.disposed is False

    await manager.dispose_all()

    assert second.disposed is True
