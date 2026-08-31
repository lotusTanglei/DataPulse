import base64
from dataclasses import dataclass, field

import pytest

from datapulse.datasource.connector import ConnectionTestResult
from datapulse.datasource.models import (
    DatasourceCreate,
    DatasourceStatus,
    DatasourceTestRequest,
    DatasourceUpdate,
    SQLiteConfig,
)
from datapulse.datasource.registry import ConnectorRegistry
from datapulse.datasource.repository import DatasourceNotFound, DatasourceRepository
from datapulse.datasource.secrets import SecretBox
from datapulse.datasource.service import DatasourceService
from datapulse.errors import DataPulseError

pytestmark = pytest.mark.anyio


@dataclass
class FakeConnector:
    type: str = "sqlite"
    dialect: str = "sqlite"
    result: ConnectionTestResult = field(
        default_factory=lambda: ConnectionTestResult(ok=True, latency_ms=12)
    )
    received_password: str | None = None

    async def test_connection(self, config: object, secret: object) -> ConnectionTestResult:
        del config
        self.received_password = None if secret is None else secret.password.get_secret_value()
        return self.result


@dataclass
class FakeEngineManager:
    disposed: list[str] = field(default_factory=list)

    async def dispose(self, datasource_id: str) -> None:
        self.disposed.append(datasource_id)


def secret_box() -> SecretBox:
    key = base64.urlsafe_b64encode(b"k" * 32).rstrip(b"=").decode()
    return SecretBox(key)


def build_service(
    repository: DatasourceRepository,
    *,
    box: SecretBox | None = None,
    connector: FakeConnector | None = None,
    manager: FakeEngineManager | None = None,
) -> tuple[DatasourceService, FakeConnector, FakeEngineManager]:
    resolved_connector = connector or FakeConnector()
    resolved_manager = manager or FakeEngineManager()
    return (
        DatasourceService(
            repository=repository,
            secret_box=box,
            registry=ConnectorRegistry([resolved_connector]),
            engine_manager=resolved_manager,
            query_executor=None,
            id_factory=lambda: "source-1",
        ),
        resolved_connector,
        resolved_manager,
    )


async def test_create_requires_master_key_and_encrypts_password(
    datasource_repository: DatasourceRepository,
) -> None:
    without_key, _, _ = build_service(datasource_repository)
    payload = DatasourceCreate(
        name="Sales",
        config=SQLiteConfig(path="sales.db"),
        password="database-password",
    )

    with pytest.raises(DataPulseError) as captured:
        await without_key.create(payload)

    assert captured.value.code == "DATASOURCE_SECRET_KEY_MISSING"
    assert await datasource_repository.list() == ()

    service, _, _ = build_service(datasource_repository, box=secret_box())
    created = await service.create(payload)
    envelope = await datasource_repository.get_secret_envelope(created.id)

    assert created.has_password is True
    assert envelope is not None
    assert "database-password" not in envelope.model_dump_json()
    assert secret_box().decrypt(created.id, envelope) == "database-password"
    assert "ciphertext" not in created.model_dump()


async def test_update_preserves_secret_and_disposes_changed_connection(
    datasource_repository: DatasourceRepository,
) -> None:
    service, connector, manager = build_service(
        datasource_repository,
        box=secret_box(),
    )
    created = await service.create(
        DatasourceCreate(
            name="Sales",
            config=SQLiteConfig(path="sales.db"),
            password="database-password",
        )
    )
    original = await datasource_repository.get_secret_envelope(created.id)

    renamed = await service.update(created.id, DatasourceUpdate(name="Renamed"))

    assert renamed.name == "Renamed"
    assert await datasource_repository.get_secret_envelope(created.id) == original
    assert manager.disposed == []

    updated = await service.update(
        created.id,
        DatasourceUpdate(config=SQLiteConfig(path="archive.db")),
    )

    assert updated.config == SQLiteConfig(path="archive.db")
    assert manager.disposed == [created.id]

    tested = await service.test_connection(created.id)
    assert tested.status is DatasourceStatus.AVAILABLE
    assert tested.last_latency_ms == 12
    assert tested.last_error_code is None
    assert tested.last_checked_at is not None
    assert connector.received_password == "database-password"


async def test_failed_connection_updates_safe_status(
    datasource_repository: DatasourceRepository,
) -> None:
    connector = FakeConnector(
        result=ConnectionTestResult(
            ok=False,
            latency_ms=7,
            error_code="DATASOURCE_CONNECTION_FAILED",
        )
    )
    service, _, _ = build_service(datasource_repository, connector=connector)
    created = await service.create(
        DatasourceCreate(name="Sales", config=SQLiteConfig(path="sales.db"))
    )

    tested = await service.test_connection(created.id)

    assert tested.status is DatasourceStatus.UNAVAILABLE
    assert tested.last_latency_ms == 7
    assert tested.last_error_code == "DATASOURCE_CONNECTION_FAILED"


async def test_unsaved_connection_test_uses_ephemeral_config(
    datasource_repository: DatasourceRepository,
) -> None:
    service, connector, _ = build_service(datasource_repository)

    result = await service.test_connection_config(
        DatasourceTestRequest(config=SQLiteConfig(path="sales.db"))
    )

    assert result.status is DatasourceStatus.AVAILABLE
    assert result.latency_ms == 12
    assert result.error_code is None
    assert connector.received_password is None
    assert await datasource_repository.list() == ()


async def test_delete_disposes_engine_after_repository_delete(
    datasource_repository: DatasourceRepository,
) -> None:
    service, _, manager = build_service(datasource_repository)
    created = await service.create(
        DatasourceCreate(name="Sales", config=SQLiteConfig(path="sales.db"))
    )

    await service.delete(created.id)

    assert manager.disposed == [created.id]
    with pytest.raises(DatasourceNotFound):
        await datasource_repository.get(created.id)
