from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from datapulse.datasource.models import SQLiteConfig
from datapulse.metadata import (
    Base,
    DataSourceRecord,
    create_metadata_engine,
    create_session_factory,
)
from datapulse.query.execution import QueryRunRepository
from datapulse.settings import Settings


@pytest.fixture
async def query_run_repository(tmp_path: Path) -> AsyncIterator[QueryRunRepository]:
    engine = create_metadata_engine(Settings(environment="test", data_dir=tmp_path))
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = create_session_factory(engine)
    async with factory.begin() as session:
        config = SQLiteConfig(path="sales.db")
        session.add(
            DataSourceRecord(
                id="source-1",
                name="Sales",
                connector_type="sqlite",
                config_json=config.model_dump(mode="json"),
            )
        )
    yield QueryRunRepository(factory)
    await engine.dispose()
