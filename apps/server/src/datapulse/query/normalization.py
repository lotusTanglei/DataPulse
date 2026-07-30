import base64
import math
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from datapulse.contracts.common import JsonValue

_max_safe_integer = 2**53 - 1


class ResultNormalizationError(ValueError):
    def __init__(self) -> None:
        super().__init__("QUERY_RESULT_TYPE_UNSUPPORTED")
        self.code = "QUERY_RESULT_TYPE_UNSUPPORTED"


def _normalize_decimal(value: Decimal) -> JsonValue:
    if value.is_finite() and value == value.to_integral_value():
        integer = int(value)
        if -_max_safe_integer <= integer <= _max_safe_integer:
            return integer
        return str(value)
    if value.is_finite():
        floating = float(value)
        if math.isfinite(floating) and Decimal(str(floating)) == value:
            return floating
    return str(value)


def normalize_result_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return _normalize_decimal(value)
    if isinstance(value, bytes):
        return base64.b64encode(value).decode()
    raise ResultNormalizationError
