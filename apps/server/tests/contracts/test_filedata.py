import pytest
from pydantic import ValidationError

from datapulse.contracts.filedata import FileAssetResponse, FileDatasetCreate


def file_asset_payload() -> dict[str, object]:
    return {
        "id": "asset-1",
        "original_name": "sales.csv",
        "format": "csv",
        "mime_type": "text/csv",
        "size_bytes": 128,
        "sha256": "a" * 64,
        "row_count": 12,
        "fields": (
            {"name": "region", "data_type": "string"},
            {"name": "amount", "data_type": "number"},
        ),
        "created_at": "2026-08-01T08:00:00Z",
    }


def file_dataset_payload() -> dict[str, object]:
    return {
        "name": "销售文件数据集",
        "file_asset_id": "asset-1",
        "sheet_name": "Sheet1",
        "max_rows": 5000,
        "timeout_seconds": 30,
    }


@pytest.mark.parametrize("file_format", ["csv", "excel", "json", "parquet"])
def test_file_asset_response_accepts_supported_formats(file_format: str) -> None:
    payload = file_asset_payload()
    payload["format"] = file_format

    asset = FileAssetResponse.model_validate(payload)

    assert asset.format == file_format
    assert asset.size_bytes > 0


def test_file_dataset_create_accepts_optional_sheet_name() -> None:
    payload = file_dataset_payload()
    payload["sheet_name"] = None

    dataset = FileDatasetCreate.model_validate(payload)

    assert dataset.sheet_name is None


@pytest.mark.parametrize("file_format", ["txt", "sqlite", ""])
def test_file_asset_response_rejects_unsupported_format(file_format: str) -> None:
    payload = file_asset_payload()
    payload["format"] = file_format

    with pytest.raises(ValidationError):
        FileAssetResponse.model_validate(payload)


@pytest.mark.parametrize("size_bytes", [0, -1])
def test_file_asset_response_rejects_non_positive_size(size_bytes: int) -> None:
    payload = file_asset_payload()
    payload["size_bytes"] = size_bytes

    with pytest.raises(ValidationError):
        FileAssetResponse.model_validate(payload)


@pytest.mark.parametrize("row_count", [-1, -10])
def test_file_asset_response_rejects_negative_row_count(row_count: int) -> None:
    payload = file_asset_payload()
    payload["row_count"] = row_count

    with pytest.raises(ValidationError):
        FileAssetResponse.model_validate(payload)


@pytest.mark.parametrize("name", ["", "   "])
def test_file_asset_response_rejects_blank_original_name(name: str) -> None:
    payload = file_asset_payload()
    payload["original_name"] = name

    with pytest.raises(ValidationError):
        FileAssetResponse.model_validate(payload)


@pytest.mark.parametrize("name", ["", "   "])
def test_file_dataset_create_rejects_blank_name(name: str) -> None:
    payload = file_dataset_payload()
    payload["name"] = name

    with pytest.raises(ValidationError):
        FileDatasetCreate.model_validate(payload)


@pytest.mark.parametrize("file_asset_id", ["", "   "])
def test_file_dataset_create_rejects_blank_asset_id(file_asset_id: str) -> None:
    payload = file_dataset_payload()
    payload["file_asset_id"] = file_asset_id

    with pytest.raises(ValidationError):
        FileDatasetCreate.model_validate(payload)
