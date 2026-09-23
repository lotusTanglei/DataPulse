from datetime import date, datetime

from datapulse.contracts.dataset import DataType
from datapulse.filedata.inference import infer_value, merge_types


def test_infer_value_coerces_scalar_text_without_losing_temporal_semantics() -> None:
    assert infer_value("true") is True
    assert infer_value("否") is False
    assert infer_value("42") == 42
    assert infer_value("3.14") == 3.14
    assert infer_value("2026-09-22") == date(2026, 9, 22)
    assert infer_value("2026-09-22T08:30:00") == datetime(2026, 9, 22, 8, 30)
    assert infer_value("  ") is None
    assert infer_value("华东") == "华东"


def test_merge_types_uses_numeric_then_temporal_then_string_fallback() -> None:
    assert merge_types(DataType.INTEGER, DataType.NUMBER) is DataType.NUMBER
    assert merge_types(DataType.DATE, DataType.DATETIME) is DataType.DATETIME
    assert merge_types(DataType.INTEGER, DataType.STRING) is DataType.STRING
    assert merge_types(DataType.BOOLEAN, DataType.INTEGER) is DataType.STRING
