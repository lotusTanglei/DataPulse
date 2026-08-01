from datapulse.contracts.filedata import FileAssetResponse
from datapulse.filedata.repository import FileAssetRepository
from datapulse.filedata.storage import FileStorage


class FileAssetService:
    def __init__(
        self,
        *,
        repository: FileAssetRepository,
        storage: FileStorage,
    ) -> None:
        self._repository = repository
        self._storage = storage

    async def ingest(self, upload, *, request_id: str) -> FileAssetResponse:
        del request_id
        stored = await self._storage.save(upload)
        asset = await self._repository.create(
            asset_id=stored.asset_id,
            original_name=stored.original_name,
            format=stored.format,
            mime_type=stored.mime_type,
            sha256=stored.sha256,
            size_bytes=stored.size_bytes,
            storage_path=stored.storage_path,
            row_count=0,
            fields_json=[],
        )
        return FileAssetResponse(
            id=asset.id,
            original_name=asset.original_name,
            format=asset.format,
            mime_type=asset.mime_type,
            size_bytes=asset.size_bytes,
            sha256=asset.sha256,
            row_count=asset.row_count,
            fields=asset.fields,
            created_at=asset.created_at,
        )
