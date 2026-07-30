from pathlib import Path

import pytest

from datapulse.metadata import (
    Base,
    SystemState,
    create_metadata_engine,
    create_session_factory,
    metadata_database_url,
)
from datapulse.settings import Settings

pytestmark = pytest.mark.anyio


async def test_metadata_database_defaults_to_data_dir(tmp_path: Path) -> None:
    settings = Settings(environment="test", data_dir=tmp_path)

    assert metadata_database_url(settings) == (
        f"sqlite+aiosqlite:///{(tmp_path / 'datapulse.db').resolve()}"
    )


async def test_session_factory_persists_system_state(tmp_path: Path) -> None:
    settings = Settings(environment="test", data_dir=tmp_path)
    engine = create_metadata_engine(settings)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = create_session_factory(engine)
    async with factory() as session:
        session.add(SystemState(id=1))
        await session.commit()
    async with factory() as session:
        assert await session.get(SystemState, 1) is not None

    await engine.dispose()
