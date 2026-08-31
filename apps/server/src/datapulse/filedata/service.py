from pathlib import Path
from time import perf_counter

from datapulse.contracts.dataset import FileFormat
from datapulse.contracts.filedata import FileAssetResponse, FilePreviewResponse
from datapulse.filedata.parsers import FileParseInvalid, excel_sheet_names, parse_file
from datapulse.filedata.repository import FileAssetRepository
from datapulse.filedata.storage import FileStorage
from datapulse.query.models import QueryColumn, QueryResult


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
        try:
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
        except Exception:
            # Parsing and metadata creation are one ingest transaction from the
            # user's perspective; do not leave files that cannot be addressed.
            try:
                self._storage.delete(stored.asset_id)
            except Exception:
                pass
            raise
        return self._response(asset)

    async def list(self) -> tuple[FileAssetResponse, ...]:
        assets = await self._repository.list()
        return tuple(self._response(asset) for asset in assets)

    async def get(self, asset_id: str):
        return await self._repository.get(asset_id)

    async def preview(
        self,
        asset_id: str,
        *,
        sheet_name: str | None,
        request_id: str,
    ) -> FilePreviewResponse:
        asset = await self._repository.get(asset_id)
        path = Path(asset.storage_path)
        sheet_names: tuple[str, ...] = ()
        selected_sheet: str | None = None
        if asset.format is FileFormat.EXCEL:
            sheet_names = await excel_sheet_names(path)
            selected_sheet = sheet_name or (sheet_names[0] if sheet_names else None)
        elif sheet_name is not None:
            raise FileParseInvalid("Sheets are only available for Excel files.")
        if selected_sheet is not None and not selected_sheet.strip():
            raise FileParseInvalid("The Excel sheet name is invalid.")

        started_at = perf_counter()
        parsed = await parse_file(
            path,
            asset.format,
            sheet_name=selected_sheet,
            max_rows=100,
        )
        fields = parsed.fields
        rows = tuple(tuple(row.get(field.name) for field in fields) for row in parsed.sample_rows)
        result = QueryResult(
            request_id=request_id,
            columns=tuple(
                QueryColumn(name=field.name, data_type=field.data_type.value) for field in fields
            ),
            rows=rows,
            row_count=len(rows),
            truncated=parsed.row_count > len(rows),
            duration_ms=max(0, int((perf_counter() - started_at) * 1000)),
        )
        return FilePreviewResponse(
            format=asset.format,
            sheet_names=sheet_names,
            selected_sheet=selected_sheet,
            result=result,
        )

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
