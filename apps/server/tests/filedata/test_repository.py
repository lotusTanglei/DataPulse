from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from datapulse.filedata.repository import FileAssetNotFound, FileAssetRepository
from datapulse.metadata import Base, create_metadata_engine, create_session_factory
from datapulse.settings import Settings

pytestmark = pytest.mark.anyio


@pytest.fixture
async def metadata_engine(tmp_path: Path) -> AsyncEngine:
    engine = create_metadata_engine(Settings(environment="test", data_dir=tmp_path))
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def metadata_session_factory(
    metadata_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(metadata_engine)


async def test_repository_round_trips_file_asset_metadata(
    metadata_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = FileAssetRepository(metadata_session_factory)

    created = await repository.create(
        asset_id="asset-1",
        original_name="sales.csv",
        format="csv",
        mime_type="text/csv",
        sha256="a" * 64,
        size_bytes=12,
        storage_path="/safe/files/asset-1/source.csv",
        row_count=3,
        fields_json=[{"name": "region", "data_type": "string"}],
    )

    assert created.id == "asset-1"
    assert created.original_name == "sales.csv"
    assert created.format == "csv"
    assert created.row_count == 3
    assert created.fields[0].name == "region"
    assert await repository.get("asset-1") == created
    assert await repository.list() == (created,)


async def test_repository_delete_and_missing_asset(
    metadata_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = FileAssetRepository(metadata_session_factory)
    await repository.create(
        asset_id="asset-1",
        original_name="sales.csv",
        format="csv",
        mime_type="text/csv",
        sha256="a" * 64,
        size_bytes=12,
        storage_path="/safe/files/asset-1/source.csv",
        row_count=3,
        fields_json=[{"name": "region", "data_type": "string"}],
    )

    await repository.delete("asset-1")

    with pytest.raises(FileAssetNotFound) as captured:
        await repository.get("asset-1")

    assert captured.value.code == "FILE_NOT_FOUND"
