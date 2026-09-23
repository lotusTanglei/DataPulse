import re
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from decimal import Decimal

from datapulse.contracts.dataset import DatasetField, DataType

type Scalar = bool | int | float | str | date | datetime | None

_INTEGER = re.compile(r"^[+-]?\d+$")
_NUMBER = re.compile(r"^[+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[eE][+-]?\d+)?$")
_TRUE = frozenset({"true", "yes", "y", "是", "对"})
_FALSE = frozenset({"false", "no", "n", "否", "不"})


def infer_value(value: object) -> Scalar:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, date, datetime)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if not isinstance(value, str):
        return value  # type: ignore[return-value]

    text = value.strip()
    if not text:
        return None
    lowered = text.casefold()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    if _INTEGER.fullmatch(text):
        return int(text)
    if _NUMBER.fullmatch(text) and ("." in text or "e" in lowered):
        return float(text)
    timestamp = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        if "T" in timestamp or " " in timestamp:
            return datetime.fromisoformat(timestamp)
    except ValueError:
        pass
    for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return value


def infer_type(value: object) -> DataType:
    normalized = infer_value(value)
    if normalized is None:
        return DataType.STRING
    if isinstance(normalized, bool):
        return DataType.BOOLEAN
    if isinstance(normalized, int) and not isinstance(normalized, bool):
        return DataType.INTEGER
    if isinstance(normalized, float):
        return DataType.NUMBER
    if isinstance(normalized, datetime):
        return DataType.DATETIME
    if isinstance(normalized, date):
        return DataType.DATE
    return DataType.STRING


def merge_types(current: DataType | None, incoming: DataType) -> DataType:
    if current is None:
        return incoming
    if current == incoming:
        return current
    if {current, incoming} <= {DataType.INTEGER, DataType.NUMBER}:
        return DataType.NUMBER
    if {current, incoming} <= {DataType.DATE, DataType.DATETIME}:
        return DataType.DATETIME
    return DataType.STRING


def coerce_row(row: Mapping[str, object]) -> dict[str, Scalar]:
    return {key: infer_value(value) for key, value in row.items()}


def coerce_rows(rows: Iterable[Mapping[str, object]]) -> list[dict[str, Scalar]]:
    return [coerce_row(row) for row in rows]


def fields_from_rows(rows: Iterable[Mapping[str, object]]) -> tuple[DatasetField, ...]:
    field_types: dict[str, DataType | None] = {}
    ordered_names: list[str] = []
    for row in rows:
        for key, value in row.items():
            if key not in field_types:
                ordered_names.append(key)
                field_types[key] = None
            field_types[key] = merge_types(field_types[key], infer_type(value))
    return tuple(
        DatasetField(name=name, data_type=field_types[name] or DataType.STRING)
        for name in ordered_names
    )
