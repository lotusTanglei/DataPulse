from enum import StrEnum
from typing import Literal

from pydantic import Field

from datapulse.contracts.common import ContractModel, JsonValue, NonBlankStr


class Aggregation(StrEnum):
    NONE = "none"
    SUM = "sum"
    AVERAGE = "average"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"


class ChartType(StrEnum):
    AREA = "area"
    BAR = "bar"
    FUNNEL = "funnel"
    GAUGE = "gauge"
    LINE = "line"
    MAP = "map"
    PIE = "pie"
    RADAR = "radar"
    SCATTER = "scatter"
    TABLE = "table"


class FilterOperator(StrEnum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    BETWEEN = "between"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class SortDirection(StrEnum):
    ASCENDING = "asc"
    DESCENDING = "desc"


class Measure(ContractModel):
    field: NonBlankStr
    aggregation: Aggregation = Aggregation.NONE


class Filter(ContractModel):
    field: NonBlankStr
    operator: FilterOperator
    value: JsonValue = None


class Sort(ContractModel):
    field: NonBlankStr
    direction: SortDirection = SortDirection.ASCENDING


class VisualSpec(ContractModel):
    type: ChartType
    title: str = ""


class ChartSpec(ContractModel):
    schema_version: Literal[1] = 1
    dataset_id: NonBlankStr
    dimensions: tuple[NonBlankStr, ...] = Field(default_factory=tuple)
    measures: tuple[Measure, ...] = Field(default_factory=tuple)
    filters: tuple[Filter, ...] = Field(default_factory=tuple)
    sort: tuple[Sort, ...] = Field(default_factory=tuple)
    limit: int = Field(default=1000, ge=1, le=5000)
    visual: VisualSpec
