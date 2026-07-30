from typing import Any

from sqlalchemy import event
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
    engine = create_async_engine(metadata_database_url(settings))
    if engine.dialect.name == "sqlite":
        event.listen(engine.sync_engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def _enable_sqlite_foreign_keys(
    dbapi_connection: Any,
    connection_record: Any,
) -> None:
    del connection_record
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
