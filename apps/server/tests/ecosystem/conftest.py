from pathlib import Path

import pytest

from datapulse.metadata import Base, create_metadata_engine, create_session_factory
from datapulse.screen.repository import ScreenRepository
from datapulse.screen.service import ScreenService
from datapulse.settings import Settings


@pytest.fixture
async def services(tmp_path: Path):
    from datapulse.ecosystem.service import EcosystemService

    engine = create_metadata_engine(Settings(environment="test", data_dir=tmp_path))
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = create_session_factory(engine)
    screens = ScreenService(repository=ScreenRepository(factory))
    ecosystem = EcosystemService(
        root=tmp_path / "ecosystem", screen_service=screens, session_factory=factory
    )
    yield ecosystem, screens, factory
    await engine.dispose()
