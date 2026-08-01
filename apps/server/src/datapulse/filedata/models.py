from datetime import datetime

from pydantic import BaseModel, ConfigDict

from datapulse.contracts.dataset import DatasetField, FileFormat


class StoredFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    asset_id: str
    original_name: str
    format: FileFormat
    mime_type: str
    sha256: str
    size_bytes: int
    storage_path: str


class StoredFileAsset(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    original_name: str
    format: FileFormat
    mime_type: str
    sha256: str
    size_bytes: int
    storage_path: str
    row_count: int
    fields: tuple[DatasetField, ...]
    created_at: datetime
