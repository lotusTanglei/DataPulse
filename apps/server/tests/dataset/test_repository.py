import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from datapulse.contracts.dataset import (
    DatasetDefinition,
    DatasetField,
    DataType,
    SqlQuery,
)
from datapulse.dataset.repository import (
    DatasetDefinitionInvalid,
    DatasetNameConflict,
    DatasetNotFound,
    DatasetRepository,
    DatasetSourceNotFound,
)
from datapulse.datasource.models import DatasourceCreate, SQLiteConfig
from datapulse.datasource.repository import DatasourceRepository
from datapulse.metadata import DatasetRecord

pytestmark = pytest.mark.anyio


def definition(
    *,
    dataset_id: str = "dataset-1",
    name: str = "Monthly sales",
    datasource_id: str = "source-1",
) -> DatasetDefinition:
    return DatasetDefinition(
        id=dataset_id,
        name=name,
        data_source_id=datasource_id,
        query=SqlQuery(sql="SELECT month, amount FROM sales"),
        fields=(
            DatasetField(name="month", data_type=DataType.STRING),
            DatasetField(name="amount", data_type=DataType.NUMBER),
        ),
    )


async def create_source(repository: DatasourceRepository) -> None:
    await repository.create(
        "source-1",
        DatasourceCreate(name="Sales", config=SQLiteConfig(path="sales.db")),
    )


async def test_repository_round_trips_canonical_definition_and_crud(
    datasource_repository: DatasourceRepository,
    metadata_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await create_source(datasource_repository)
    repository = DatasetRepository(metadata_session_factory)

    created = await repository.create(definition())

    assert created.id == "dataset-1"
    assert created.name == "Monthly sales"
    assert created.data_source_id == "source-1"
    assert created.definition == definition()
    assert created.created_at.tzinfo is not None
    assert created.updated_at.tzinfo is not None
    assert await repository.get("dataset-1") == created
    assert await repository.list() == (created,)

    async with metadata_session_factory() as session:
        stored = await session.scalar(
            select(DatasetRecord.definition_json).where(DatasetRecord.id == "dataset-1")
        )
    assert list(stored) == sorted(stored)

    replacement = definition(name="Renamed")
    updated = await repository.update("dataset-1", replacement)
    assert updated.name == "Renamed"
    assert updated.definition == replacement
    assert updated.updated_at >= created.updated_at

    await repository.delete("dataset-1")
    with pytest.raises(DatasetNotFound):
        await repository.get("dataset-1")


async def test_repository_maps_unique_name_and_source_foreign_key(
    datasource_repository: DatasourceRepository,
    metadata_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await create_source(datasource_repository)
    repository = DatasetRepository(metadata_session_factory)
    await repository.create(definition())

    with pytest.raises(DatasetNameConflict):
        await repository.create(definition(dataset_id="dataset-2", name="Monthly sales"))
    with pytest.raises(DatasetSourceNotFound):
        await repository.create(
            definition(
                dataset_id="dataset-3",
                name="Missing source",
                datasource_id="missing",
            )
        )


async def test_corrupt_definition_maps_to_stable_domain_error(
    datasource_repository: DatasourceRepository,
    metadata_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await create_source(datasource_repository)
    repository = DatasetRepository(metadata_session_factory)
    await repository.create(definition())
    async with metadata_session_factory.begin() as session:
        await session.execute(
            update(DatasetRecord)
            .where(DatasetRecord.id == "dataset-1")
            .values(definition_json={"schema_version": 999})
        )

    with pytest.raises(DatasetDefinitionInvalid) as captured:
        await repository.get("dataset-1")

    assert captured.value.code == "DATASET_DEFINITION_INVALID"
