from pathlib import Path

from datapulse.contracts.filedata import FileAssetResponse
from datapulse.filedata.parsers import parse_file
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

    @staticmethod
    def _response(asset) -> FileAssetResponse:
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

    async def ingest(self, upload, *, request_id: str) -> FileAssetResponse:
        del request_id
        stored = await self._storage.save(upload)
        parsed = await parse_file(
            Path(stored.storage_path),
            stored.format,
            sheet_name=None,
            max_rows=5000,
        )
        asset = await self._repository.create(
            asset_id=stored.asset_id,
            original_name=stored.original_name,
            format=stored.format,
            mime_type=stored.mime_type,
            sha256=stored.sha256,
            size_bytes=stored.size_bytes,
            storage_path=stored.storage_path,
            row_count=parsed.row_count,
            fields_json=[field.model_dump(mode="json") for field in parsed.fields],
        )
        return self._response(asset)

    async def list(self) -> tuple[FileAssetResponse, ...]:
        assets = await self._repository.list()
        return tuple(self._response(asset) for asset in assets)

    async def get(self, asset_id: str):
        return await self._repository.get(asset_id)

    async def delete(self, asset_id: str) -> None:
        await self._repository.get(asset_id)
        if await self._repository.is_referenced(asset_id):
            from datapulse.filedata.repository import FileInUse

            raise FileInUse(asset_id)
        await self._repository.delete(asset_id)
        self._storage.delete(asset_id)

    async def update_parsed_metadata(
        self,
        asset_id: str,
        *,
        row_count: int,
        fields,
    ):
        asset = await self._repository.update_parsed(
            asset_id,
            row_count=row_count,
            fields_json=[field.model_dump(mode="json") for field in fields],
        )
        return self._response(asset)
