from collections.abc import AsyncIterator

import pytest

from datapulse.metadata import Base, create_metadata_engine, create_session_factory
from datapulse.settings import Settings
from datapulse.speech.repository import SpeechRepository


@pytest.fixture
async def speech_repository(tmp_path) -> AsyncIterator[SpeechRepository]:
    settings = Settings(
        environment="test",
        data_dir=tmp_path,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'speech.db'}",
    )
    engine = create_metadata_engine(settings)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield SpeechRepository(create_session_factory(engine))
    await engine.dispose()
