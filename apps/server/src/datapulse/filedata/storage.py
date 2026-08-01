import hashlib
import os
import tempfile
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from datapulse.filedata.models import StoredFile
from datapulse.settings import Settings

_FORMAT_MAP = {
    ".csv": {
        "format": "csv",
        "mime_types": {"text/csv", "application/csv", "application/vnd.ms-excel"},
    },
    ".json": {
        "format": "json",
        "mime_types": {"application/json", "text/json"},
    },
    ".parquet": {
        "format": "parquet",
        "mime_types": {"application/vnd.apache.parquet", "application/octet-stream"},
    },
    ".xlsx": {
        "format": "excel",
        "mime_types": {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        },
    },
    ".xls": {
        "format": "excel",
        "mime_types": {"application/vnd.ms-excel"},
    },
}


class FileTypeUnsupported(ValueError):
    code = "FILE_TYPE_UNSUPPORTED"


class FileTooLarge(ValueError):
    code = "FILE_TOO_LARGE"


class FileEmpty(ValueError):
    code = "FILE_EMPTY"


class FileNotFound(LookupError):
    code = "FILE_NOT_FOUND"


class FileStorage:
    def __init__(
        self,
        settings: Settings,
        *,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._settings = settings
        self._files_dir = settings.resolved_files_dir()
        self._id_factory = id_factory or (lambda: str(uuid4()))

    async def save(self, upload) -> StoredFile:
        filename = (getattr(upload, "filename", "") or "").strip()
        content_type = (getattr(upload, "content_type", "") or "").partition(";")[0].strip().lower()
        extension = Path(filename).suffix.lower()
        file_config = _FORMAT_MAP.get(extension)
        if file_config is None or content_type not in file_config["mime_types"]:
            raise FileTypeUnsupported("The file format is not supported.")

        asset_id = self._id_factory()
        asset_dir = (self._files_dir / asset_id).resolve()
        self._files_dir.mkdir(parents=True, exist_ok=True)
        asset_dir.mkdir(parents=True, exist_ok=False)

        descriptor: int | None = None
        temp_path: Path | None = None
        size_bytes = 0
        digest = hashlib.sha256()
        try:
            descriptor, raw_temp_path = tempfile.mkstemp(dir=asset_dir, prefix="upload-", suffix=".tmp")
            temp_path = Path(raw_temp_path).resolve()
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = None
                while True:
                    chunk = await upload.read(1024 * 1024)
                    if not chunk:
                        break
                    size_bytes += len(chunk)
                    if size_bytes > self._settings.file_max_bytes:
                        raise FileTooLarge("The file exceeds the configured size limit.")
                    digest.update(chunk)
                    handle.write(chunk)
            if size_bytes == 0:
                raise FileEmpty("The uploaded file is empty.")

            storage_path = (asset_dir / f"source{extension}").resolve()
            if not storage_path.is_relative_to(asset_dir):
                raise FileTypeUnsupported("The file path is invalid.")
            temp_path.replace(storage_path)
            return StoredFile(
                asset_id=asset_id,
                original_name=filename,
                format=file_config["format"],
                mime_type=content_type,
                sha256=digest.hexdigest(),
                size_bytes=size_bytes,
                storage_path=str(storage_path),
            )
        except Exception:
            if descriptor is not None:
                os.close(descriptor)
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            for child in asset_dir.glob("*"):
                child.unlink(missing_ok=True)
            asset_dir.rmdir()
            raise

    @contextmanager
    def open_read(self, asset_id: str) -> Generator[object, None, None]:
        asset_dir = (self._files_dir / asset_id).resolve()
        if not asset_dir.exists() or not asset_dir.is_dir() or not asset_dir.is_relative_to(self._files_dir):
            raise FileNotFound(asset_id)
        candidates = [path for path in asset_dir.iterdir() if path.name.startswith("source.")]
        if len(candidates) != 1:
            raise FileNotFound(asset_id)
        candidate = candidates[0]
        if candidate.is_symlink():
            raise FileNotFound(asset_id)
        resolved = candidate.resolve(strict=True)
        if not resolved.is_file() or not resolved.is_relative_to(asset_dir):
            raise FileNotFound(asset_id)
        with resolved.open("rb") as handle:
            yield handle

    def delete(self, asset_id: str) -> None:
        asset_dir = (self._files_dir / asset_id).resolve()
        if not asset_dir.exists() or not asset_dir.is_dir() or not asset_dir.is_relative_to(self._files_dir):
            raise FileNotFound(asset_id)
        for child in asset_dir.iterdir():
            child.unlink(missing_ok=True)
        asset_dir.rmdir()
