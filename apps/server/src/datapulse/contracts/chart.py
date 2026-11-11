from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from datapulse.contracts.common import ContractModel, JsonValue, NonBlankStr
from datapulse.contracts.dataset import TimeGrain


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


class TimeBucket(ContractModel):
    field: NonBlankStr
    grain: TimeGrain | None = None
    parameter: NonBlankStr | None = None

    @model_validator(mode="after")
    def require_grain_or_parameter(self) -> Self:
        if (self.grain is None) == (self.parameter is None):
            raise ValueError("Exactly one grain or parameter is required.")
        return self


class DrillDownLevel(ContractModel):
    field: NonBlankStr
    selection_parameter: NonBlankStr


class DrillDownSpec(ContractModel):
    level_parameter: NonBlankStr
    levels: tuple[DrillDownLevel, ...] = Field(min_length=2, max_length=8)

    @model_validator(mode="after")
    def validate_levels(self) -> Self:
        fields = [level.field for level in self.levels]
        parameters = [level.selection_parameter for level in self.levels]
        if len(fields) != len(set(fields)):
            raise ValueError("Drill-down fields must be unique.")
        if len(parameters) != len(set(parameters)):
            raise ValueError("Drill-down selection parameters must be unique.")
        return self


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
    time_buckets: tuple[TimeBucket, ...] = Field(default_factory=tuple, max_length=3)
    drill_down: DrillDownSpec | None = None
    limit: int = Field(default=1000, ge=1, le=5000)
    visual: VisualSpec

    @model_validator(mode="after")
    def validate_scenario_controls(self) -> Self:
        bucket_fields = [bucket.field for bucket in self.time_buckets]
        if len(bucket_fields) != len(set(bucket_fields)):
            raise ValueError("Time bucket fields must be unique.")
        if not set(bucket_fields) <= set(self.dimensions):
            raise ValueError("Time buckets must reference chart dimensions.")
        if self.drill_down is not None and self.drill_down.levels[0].field not in self.dimensions:
            raise ValueError("The first drill-down field must be a chart dimension.")
        return self
