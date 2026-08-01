from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from datapulse.contracts.dataset import DatasetField
from datapulse.filedata.models import StoredFileAsset
from datapulse.metadata import FileAssetRecord


class FileAssetNotFound(LookupError):
    code = "FILE_NOT_FOUND"


class FileAssetRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _to_asset(record: FileAssetRecord) -> StoredFileAsset:
        return StoredFileAsset(
            id=record.id,
            original_name=record.original_name,
            format=record.format,
            mime_type=record.mime_type,
            sha256=record.sha256,
            size_bytes=record.size_bytes,
            storage_path=record.storage_path,
            row_count=record.row_count,
            fields=tuple(DatasetField.model_validate(field) for field in record.fields_json),
            created_at=record.created_at,
        )

    async def create(
        self,
        *,
        asset_id: str,
        original_name: str,
        format: str,
        mime_type: str,
        sha256: str,
        size_bytes: int,
        storage_path: str,
        row_count: int,
        fields_json: list[dict[str, object]],
    ) -> StoredFileAsset:
        record = FileAssetRecord(
            id=asset_id,
            original_name=original_name,
            format=format,
            mime_type=mime_type,
            sha256=sha256,
            size_bytes=size_bytes,
            storage_path=storage_path,
            row_count=row_count,
            fields_json=fields_json,
        )
        async with self._session_factory.begin() as session:
            session.add(record)
            await session.flush()
        return self._to_asset(record)

    async def get(self, asset_id: str) -> StoredFileAsset:
        async with self._session_factory() as session:
            record = await session.get(FileAssetRecord, asset_id)
        if record is None:
            raise FileAssetNotFound(asset_id)
        return self._to_asset(record)

    async def list(self) -> tuple[StoredFileAsset, ...]:
        async with self._session_factory() as session:
            records = (
                await session.scalars(
                    select(FileAssetRecord).order_by(FileAssetRecord.created_at, FileAssetRecord.id)
                )
            ).all()
        return tuple(self._to_asset(record) for record in records)

    async def delete(self, asset_id: str) -> None:
        async with self._session_factory.begin() as session:
            result = await session.execute(delete(FileAssetRecord).where(FileAssetRecord.id == asset_id))
            if not result.rowcount:
                raise FileAssetNotFound(asset_id)
