from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from datapulse.settings import Settings


def metadata_database_url(settings: Settings) -> str:
    if settings.database_url is not None:
        return settings.database_url
    database_path = (settings.data_dir / "datapulse.db").resolve()
    return f"sqlite+aiosqlite:///{database_path}"


def create_metadata_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(metadata_database_url(settings))


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
