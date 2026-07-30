from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from datapulse.metadata import DisplayAccessRecord, ScreenRecord
from datapulse.metadata.models import utc_now
from datapulse.screen.repository import ScreenNotFound


class DisplayKeyNotFound(LookupError):
    pass


@dataclass(frozen=True)
class StoredDisplayAccess:
    screen_id: str
    key_hash: str
    key_version: int
    created_at: datetime
    updated_at: datetime


class DisplayAccessRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _to_access(record: DisplayAccessRecord) -> StoredDisplayAccess:
        return StoredDisplayAccess(
            screen_id=record.screen_id,
            key_hash=record.key_hash,
            key_version=record.key_version,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    async def rotate(self, screen_id: str, key_hash: str) -> StoredDisplayAccess:
        async with self._session_factory.begin() as session:
            if await session.get(ScreenRecord, screen_id) is None:
                raise ScreenNotFound(screen_id)
            record = await session.get(DisplayAccessRecord, screen_id)
            if record is None:
                record = DisplayAccessRecord(
                    screen_id=screen_id,
                    key_hash=key_hash,
                    key_version=1,
                )
                session.add(record)
            else:
                record.key_hash = key_hash
                record.key_version += 1
                record.updated_at = utc_now()
            await session.flush()
        return self._to_access(record)

    async def get(self, screen_id: str) -> StoredDisplayAccess:
        async with self._session_factory() as session:
            record = await session.get(DisplayAccessRecord, screen_id)
        if record is None:
            raise DisplayKeyNotFound(screen_id)
        return self._to_access(record)


__all__ = [
    "DisplayAccessRepository",
    "DisplayKeyNotFound",
    "StoredDisplayAccess",
]
