import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from datapulse.datasource.models import (
    DatasourceCreate,
    DatasourceStatus,
    DatasourceUpdate,
    SQLiteConfig,
)
from datapulse.datasource.repository import (
    DatasourceInUse,
    DatasourceNameConflict,
    DatasourceNotFound,
    DatasourceRepository,
)
from datapulse.datasource.secrets import SecretEnvelope
from datapulse.metadata import DatasetRecord

pytestmark = pytest.mark.anyio


def create_payload(name: str = "Sales") -> DatasourceCreate:
    return DatasourceCreate(
        name=name,
        config=SQLiteConfig(path="sales.db"),
    )


def envelope(ciphertext: str = "ciphertext") -> SecretEnvelope:
    return SecretEnvelope(nonce="bm9uY2U", ciphertext=ciphertext)


async def test_repository_create_list_and_get_return_safe_responses(
    datasource_repository: DatasourceRepository,
) -> None:
    created = await datasource_repository.create(
        "source-1",
        create_payload(),
        secret_envelope=envelope(),
    )

    assert created.id == "source-1"
    assert created.name == "Sales"
    assert created.status is DatasourceStatus.UNKNOWN
    assert created.has_password is True
    assert created.config == SQLiteConfig(path="sales.db")
    assert await datasource_repository.get("source-1") == created
    assert await datasource_repository.list() == (created,)
    assert "ciphertext" not in created.model_dump()


async def test_repository_maps_duplicate_names_to_domain_error(
    datasource_repository: DatasourceRepository,
) -> None:
    await datasource_repository.create("source-1", create_payload())

    with pytest.raises(DatasourceNameConflict):
        await datasource_repository.create("source-2", create_payload())


async def test_update_preserves_replaces_and_clears_password(
    datasource_repository: DatasourceRepository,
) -> None:
    original = envelope("b3JpZ2luYWw")
    replacement = envelope("cmVwbGFjZW1lbnQ")
    await datasource_repository.create(
        "source-1",
        create_payload(),
        secret_envelope=original,
    )

    updated = await datasource_repository.update(
        "source-1",
        DatasourceUpdate(
            name="Renamed",
            config=SQLiteConfig(path="renamed.db"),
        ),
    )
    assert updated.name == "Renamed"
    assert updated.has_password is True
    assert await datasource_repository.get_secret_envelope("source-1") == original

    replaced = await datasource_repository.update(
        "source-1",
        DatasourceUpdate(password="replacement-password"),
        secret_envelope=replacement,
    )
    assert replaced.has_password is True
    assert await datasource_repository.get_secret_envelope("source-1") == replacement

    cleared = await datasource_repository.update(
        "source-1",
        DatasourceUpdate(clear_password=True),
    )
    assert cleared.has_password is False
    assert await datasource_repository.get_secret_envelope("source-1") is None


async def test_repository_update_and_delete_unknown_source(
    datasource_repository: DatasourceRepository,
) -> None:
    with pytest.raises(DatasourceNotFound):
        await datasource_repository.update("missing", DatasourceUpdate(name="New"))
    with pytest.raises(DatasourceNotFound):
        await datasource_repository.delete("missing")


async def test_delete_removes_source(
    datasource_repository: DatasourceRepository,
) -> None:
    await datasource_repository.create("source-1", create_payload())

    await datasource_repository.delete("source-1")

    with pytest.raises(DatasourceNotFound):
        await datasource_repository.get("source-1")


async def test_delete_maps_dataset_dependency_to_conflict(
    datasource_repository: DatasourceRepository,
    metadata_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await datasource_repository.create("source-1", create_payload())
    async with metadata_session_factory.begin() as session:
        session.add(
            DatasetRecord(
                id="dataset-1",
                name="Sales dataset",
                data_source_id="source-1",
                definition_json={"schema_version": 1},
            )
        )

    with pytest.raises(DatasourceInUse):
        await datasource_repository.delete("source-1")
