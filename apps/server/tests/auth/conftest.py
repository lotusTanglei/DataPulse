from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from datapulse.auth.repository import AuthRepository
from datapulse.metadata import Base, create_metadata_engine, create_session_factory
from datapulse.settings import Settings


@pytest.fixture
async def auth_repository(tmp_path: Path) -> AsyncIterator[AuthRepository]:
    settings = Settings(environment="test", data_dir=tmp_path)
    engine: AsyncEngine = create_metadata_engine(settings)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield AuthRepository(create_session_factory(engine))

    await engine.dispose()
