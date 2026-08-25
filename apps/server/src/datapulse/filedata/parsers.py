import asyncio
import csv
import io
import json
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path

import openpyxl
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict

from datapulse.contracts.common import JsonValue
from datapulse.contracts.dataset import DatasetField, DataType, FileFormat


class FileParseInvalid(ValueError):
    code = "FILE_PARSE_INVALID"


class ParsedFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    fields: tuple[DatasetField, ...]
    row_count: int
    sample_rows: tuple[dict[str, JsonValue], ...]
    normalized_path: Path


def _merge_type(current: DataType | None, value: object) -> DataType:
    if value is None:
        return current or DataType.STRING
    inferred: DataType
    if isinstance(value, bool):
        inferred = DataType.BOOLEAN
    elif isinstance(value, int) and not isinstance(value, bool):
        inferred = DataType.INTEGER
    elif isinstance(value, float):
        inferred = DataType.NUMBER
    elif isinstance(value, datetime):
        inferred = DataType.DATETIME
    elif isinstance(value, date):
        inferred = DataType.DATE
    else:
        inferred = DataType.STRING
    if current is None:
        return inferred
    if current == inferred:
        return current
    if {current, inferred} <= {DataType.INTEGER, DataType.NUMBER}:
        return DataType.NUMBER
    if {current, inferred} <= {DataType.DATE, DataType.DATETIME}:
        return DataType.DATETIME
    return DataType.STRING


def _normalize_value(value: object) -> JsonValue:
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raise FileParseInvalid("The file contains unsupported nested values.")


def _fields_from_rows(rows: Iterable[dict[str, object]]) -> tuple[DatasetField, ...]:
    field_types: dict[str, DataType | None] = {}
    ordered_names: list[str] = []
    for row in rows:
        for key, value in row.items():
            if key not in field_types:
                ordered_names.append(key)
                field_types[key] = None
            field_types[key] = _merge_type(field_types[key], value)
    return tuple(
        DatasetField(name=name, data_type=field_types[name] or DataType.STRING)
        for name in ordered_names
    )


def _write_parquet(rows: list[dict[str, object]], target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), target)
    return target


def _detect_text(data: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise FileParseInvalid("The file encoding is not supported.")


def _parse_csv(path: Path, *, max_rows: int) -> ParsedFile:
    raw = path.read_bytes()
    text, encoding = _detect_text(raw)
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise FileParseInvalid("The CSV header is invalid.")
    rows: list[dict[str, object]] = []
    for raw_row in reader:
        row = {key: value for key, value in raw_row.items() if key}
        rows.append(row)
    fields = _fields_from_rows(rows)
    normalized_path = path
    if encoding not in {"utf-8", "utf-8-sig"}:
        normalized_path = path.with_suffix(".normalized.csv")
        normalized_path.write_text(text, encoding="utf-8")
    return ParsedFile(
        fields=fields,
        row_count=len(rows),
        sample_rows=tuple(
            {key: _normalize_value(value) for key, value in row.items()} for row in rows[:max_rows]
        ),
        normalized_path=normalized_path,
    )


def _parse_excel(path: Path, *, sheet_name: str | None, max_rows: int) -> ParsedFile:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        if sheet_name is not None and sheet_name not in workbook.sheetnames:
            raise FileParseInvalid("The Excel sheet does not exist.")
        worksheet = workbook[sheet_name] if sheet_name is not None else workbook.active
        rows_iter = worksheet.iter_rows(values_only=True)
        try:
            header_row = next(rows_iter)
        except StopIteration as error:
            raise FileParseInvalid("The Excel sheet is empty.") from error
        headers = [str(cell).strip() if cell is not None else "" for cell in header_row]
        if not any(headers) or any(not header for header in headers):
            raise FileParseInvalid("The Excel header is invalid.")
        rows: list[dict[str, object]] = []
        for values in rows_iter:
            row = {headers[index]: value for index, value in enumerate(values)}
            rows.append(row)
        normalized_path = path.with_suffix(f".{worksheet.title}.parquet")
        _write_parquet(rows, normalized_path)
        return ParsedFile(
            fields=_fields_from_rows(rows),
            row_count=len(rows),
            sample_rows=tuple(
                {key: _normalize_value(value) for key, value in row.items()}
                for row in rows[:max_rows]
            ),
            normalized_path=normalized_path,
        )
    finally:
        workbook.close()


def _excel_sheet_names_sync(path: Path) -> tuple[str, ...]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        return tuple(workbook.sheetnames)
    finally:
        workbook.close()


async def excel_sheet_names(path: Path) -> tuple[str, ...]:
    return await asyncio.to_thread(_excel_sheet_names_sync, path)


def _parse_json(path: Path, *, max_rows: int) -> ParsedFile:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise FileParseInvalid("JSON must be a non-empty object array.")
    rows: list[dict[str, object]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise FileParseInvalid("JSON rows must be objects.")
        if any(isinstance(value, (dict, list)) for value in item.values()):
            raise FileParseInvalid("Nested JSON objects are not supported.")
        rows.append(item)
    normalized_path = path.with_suffix(".normalized.parquet")
    _write_parquet(rows, normalized_path)
    return ParsedFile(
        fields=_fields_from_rows(rows),
        row_count=len(rows),
        sample_rows=tuple(
            {key: _normalize_value(value) for key, value in row.items()} for row in rows[:max_rows]
        ),
        normalized_path=normalized_path,
    )


def _map_arrow_type(arrow_type: pa.DataType) -> DataType:
    if pa.types.is_boolean(arrow_type):
        return DataType.BOOLEAN
    if pa.types.is_date(arrow_type):
        return DataType.DATE
    if pa.types.is_timestamp(arrow_type):
        return DataType.DATETIME
    if pa.types.is_integer(arrow_type):
        return DataType.INTEGER
    if pa.types.is_floating(arrow_type) or pa.types.is_decimal(arrow_type):
        return DataType.NUMBER
    return DataType.STRING


def _parse_parquet(path: Path, *, max_rows: int) -> ParsedFile:
    table = pq.read_table(path)
    fields = tuple(
        DatasetField(name=field.name, data_type=_map_arrow_type(field.type))
        for field in table.schema
    )
    sample_rows = tuple(
        {key: _normalize_value(value) for key, value in row.items()}
        for row in table.slice(0, max_rows).to_pylist()
    )
    return ParsedFile(
        fields=fields,
        row_count=table.num_rows,
        sample_rows=sample_rows,
        normalized_path=path,
    )


def _parse_sync(
    path: Path,
    file_format: FileFormat,
    *,
    sheet_name: str | None,
    max_rows: int,
) -> ParsedFile:
    if file_format is FileFormat.CSV:
        return _parse_csv(path, max_rows=max_rows)
    if file_format is FileFormat.EXCEL:
        return _parse_excel(path, sheet_name=sheet_name, max_rows=max_rows)
    if file_format is FileFormat.JSON:
        return _parse_json(path, max_rows=max_rows)
    if file_format is FileFormat.PARQUET:
        return _parse_parquet(path, max_rows=max_rows)
    raise FileParseInvalid("The file format is not supported.")


async def parse_file(
    path: Path,
    file_format: FileFormat,
    *,
    sheet_name: str | None,
    max_rows: int,
) -> ParsedFile:
    return await asyncio.to_thread(
        _parse_sync,
        path,
        file_format,
        sheet_name=sheet_name,
        max_rows=max_rows,
    )
