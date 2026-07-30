from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from datapulse.metadata import Base, create_metadata_engine, create_session_factory
from datapulse.screen.repository import ScreenRepository
from datapulse.settings import Settings


@pytest.fixture
async def metadata_engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
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


@pytest.fixture
def screen_repository(
    metadata_session_factory: async_sessionmaker[AsyncSession],
) -> ScreenRepository:
    return ScreenRepository(metadata_session_factory)
