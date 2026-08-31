from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from datapulse.contracts.common import ContractModel, JsonValue, NonBlankStr


class Aggregation(StrEnum):
    SUM = "sum"
    AVERAGE = "avg"
    MINIMUM = "min"
    MAXIMUM = "max"
    COUNT = "count"


class ChartType(StrEnum):
    AREA = "area"
    BAR = "bar"
    FUNNEL = "funnel"
    GAUGE = "gauge"
    HEATMAP = "heatmap"
    KPI = "kpi"
    LINE = "line"
    MAP = "map"
    PIE = "pie"
    PROGRESS = "progress"
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
    aggregation: Aggregation


class ParameterRef(ContractModel):
    kind: Literal["parameter"] = "parameter"
    name: NonBlankStr


class LiteralValue(ContractModel):
    kind: Literal["literal"] = "literal"
    value: JsonValue = None


FilterValue = Annotated[
    ParameterRef | LiteralValue,
    Field(discriminator="kind"),
]


class Filter(ContractModel):
    field: NonBlankStr
    operator: FilterOperator
    value: FilterValue = Field(default_factory=LiteralValue)


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
