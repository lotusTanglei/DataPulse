from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from datapulse.metadata import EmbedAccessRecord
from datapulse.metadata.models import utc_now

EMBED_ACCESS_ID = 1


class EmbedApiKeyNotFound(LookupError):
    pass


@dataclass(frozen=True)
class StoredEmbedAccess:
    api_key_hash: str
    key_version: int
    created_at: datetime
    updated_at: datetime


class EmbedAccessRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _to_access(record: EmbedAccessRecord) -> StoredEmbedAccess:
        return StoredEmbedAccess(
            api_key_hash=record.api_key_hash,
            key_version=record.key_version,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    async def rotate(self, api_key_hash: str) -> StoredEmbedAccess:
        async with self._session_factory.begin() as session:
            record = await session.get(EmbedAccessRecord, EMBED_ACCESS_ID)
            if record is None:
                record = EmbedAccessRecord(
                    id=EMBED_ACCESS_ID,
                    api_key_hash=api_key_hash,
                    key_version=1,
                )
                session.add(record)
            else:
                record.api_key_hash = api_key_hash
                record.key_version += 1
                record.updated_at = utc_now()
            await session.flush()
        return self._to_access(record)

    async def get(self) -> StoredEmbedAccess:
        async with self._session_factory() as session:
            record = await session.get(EmbedAccessRecord, EMBED_ACCESS_ID)
        if record is None:
            raise EmbedApiKeyNotFound
        return self._to_access(record)


__all__ = [
    "EMBED_ACCESS_ID",
    "EmbedAccessRepository",
    "EmbedApiKeyNotFound",
    "StoredEmbedAccess",
]
