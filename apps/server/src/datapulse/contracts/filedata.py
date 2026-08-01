from datetime import datetime

from pydantic import Field

from datapulse.contracts.common import ContractModel, NonBlankStr, PositiveInt
from datapulse.contracts.dataset import DatasetField, FileFormat


class FileAssetResponse(ContractModel):
    id: NonBlankStr
    original_name: NonBlankStr
    format: FileFormat
    mime_type: NonBlankStr
    size_bytes: PositiveInt
    sha256: NonBlankStr
    row_count: int = Field(ge=0)
    fields: tuple[DatasetField, ...] = Field(default_factory=tuple)
    created_at: datetime


class FileDatasetCreate(ContractModel):
    name: NonBlankStr
    file_asset_id: NonBlankStr
    sheet_name: NonBlankStr | None = None
    max_rows: PositiveInt = Field(default=5000, le=5000)
    timeout_seconds: PositiveInt = Field(default=30, le=300)
