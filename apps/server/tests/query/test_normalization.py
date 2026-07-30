import base64
from datetime import UTC, date, datetime
from decimal import Decimal
from math import inf, nan
from uuid import UUID

import pytest

from datapulse.query.normalization import (
    ResultNormalizationError,
    normalize_result_value,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (True, True),
        (42, 42),
        (1.5, 1.5),
        ("sales", "sales"),
        (UUID("12345678-1234-5678-1234-567812345678"), "12345678-1234-5678-1234-567812345678"),
        (date(2026, 7, 30), "2026-07-30"),
        (
            datetime(2026, 7, 30, 8, 0, tzinfo=UTC),
            "2026-07-30T08:00:00+00:00",
        ),
        (datetime(2026, 7, 30, 8, 0), "2026-07-30T08:00:00"),
        (Decimal("42"), 42),
        (Decimal("12.5"), 12.5),
        (Decimal("9007199254740992"), "9007199254740992"),
        (Decimal("12.5000000000000000001"), "12.5000000000000000001"),
        (b"\x00\xff", base64.b64encode(b"\x00\xff").decode()),
        (nan, None),
        (inf, None),
        (-inf, None),
    ],
)
def test_supported_result_values_are_json_safe(value: object, expected: object) -> None:
    assert normalize_result_value(value) == expected


def test_unsupported_result_value_uses_stable_error() -> None:
    with pytest.raises(ResultNormalizationError) as captured:
        normalize_result_value(object())

    assert captured.value.code == "QUERY_RESULT_TYPE_UNSUPPORTED"
