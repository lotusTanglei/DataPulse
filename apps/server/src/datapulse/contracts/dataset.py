from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, HttpUrl, field_validator, model_validator

from datapulse.contracts.common import ContractModel, JsonValue, NonBlankStr


class DataType(StrEnum):
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    INTEGER = "integer"
    NUMBER = "number"
    STRING = "string"


class FileFormat(StrEnum):
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    PARQUET = "parquet"


class TableQuery(ContractModel):
    kind: Literal["table"] = "table"
    table: NonBlankStr
    schema_name: str | None = None


class SqlQuery(ContractModel):
    kind: Literal["sql"] = "sql"
    sql: NonBlankStr


class FileQuery(ContractModel):
    kind: Literal["file"] = "file"
    asset_id: NonBlankStr
    format: FileFormat
    sheet_name: NonBlankStr | None = None


class RestQuery(ContractModel):
    kind: Literal["rest"] = "rest"
    method: Literal["GET", "POST"] = "GET"
    url: HttpUrl
    query: dict[str, JsonValue] = Field(default_factory=dict)
    body: JsonValue | None = None
    response_path: str | None = None

    @field_validator("response_path")
    @classmethod
    def _validate_response_path(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("response_path must not be blank")
        return value


QueryDefinition = Annotated[
    TableQuery | SqlQuery | FileQuery | RestQuery,
    Field(discriminator="kind"),
]


class DatasetField(ContractModel):
    name: NonBlankStr
    data_type: DataType


class DatasetFieldOverride(ContractModel):
    name: NonBlankStr
    data_type: DataType | None = None
    role: Literal[
        "identifier",
        "dimension",
        "measure",
        "geography",
        "temporal",
        "text",
        "boolean",
        "unknown",
    ] | None = None
    default_aggregation: Literal["sum", "avg", "min", "max", "count"] | None = None
    unit: NonBlankStr | None = None
    display_name: NonBlankStr | None = None
    format: NonBlankStr | None = None
    aliases: tuple[NonBlankStr, ...] = Field(default_factory=tuple)

    @field_validator("aliases")
    @classmethod
    def _validate_aliases(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("Field aliases must be unique.")
        return value


class CalculationOperator(StrEnum):
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"


class CalculatedFieldExpression(ContractModel):
    left_field: NonBlankStr
    operator: CalculationOperator
    right_field: NonBlankStr | None = None
    constant: float | None = None

    @model_validator(mode="after")
    def require_one_right_operand(self) -> "CalculatedFieldExpression":
        if (self.right_field is None) == (self.constant is None):
            raise ValueError("Exactly one right_field or constant is required.")
        if self.operator is CalculationOperator.DIVIDE and self.constant == 0:
            raise ValueError("Division by zero is not allowed.")
        return self


class DatasetCalculatedField(ContractModel):
    name: NonBlankStr
    label: NonBlankStr
    data_type: DataType
    expression: CalculatedFieldExpression
    unit: NonBlankStr | None = None
    format: NonBlankStr | None = None

    @model_validator(mode="after")
    def require_numeric_type(self) -> "DatasetCalculatedField":
        if self.data_type not in {DataType.INTEGER, DataType.NUMBER}:
            raise ValueError("Calculated fields must have a numeric data type.")
        return self


class DatasetMetric(ContractModel):
    name: NonBlankStr
    label: NonBlankStr
    source_field: NonBlankStr
    aggregation: Literal["sum", "avg", "min", "max", "count"]
    unit: NonBlankStr | None = None
    format: NonBlankStr | None = None
    description: NonBlankStr | None = None


class DatasetRelationship(ContractModel):
    name: NonBlankStr
    target_dataset_id: NonBlankStr
    local_field: NonBlankStr
    target_field: NonBlankStr
    cardinality: Literal["one_to_one", "one_to_many", "many_to_one"]


class TimeGrain(StrEnum):
    YEAR = "year"
    QUARTER = "quarter"
    MONTH = "month"
    WEEK = "week"
    DAY = "day"
    HOUR = "hour"


class DatasetHierarchyLevel(ContractModel):
    field: NonBlankStr
    label: NonBlankStr
    time_grain: TimeGrain | None = None


class DatasetHierarchy(ContractModel):
    name: NonBlankStr
    label: NonBlankStr
    kind: Literal["dimension", "time"]
    levels: tuple[DatasetHierarchyLevel, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_levels(self) -> "DatasetHierarchy":
        fields = [level.field for level in self.levels]
        if len(fields) != len(set(fields)):
            raise ValueError("Hierarchy fields must be unique.")
        if self.kind == "time" and any(level.time_grain is None for level in self.levels):
            raise ValueError("Time hierarchy levels require time_grain.")
        if self.kind == "dimension" and any(
            level.time_grain is not None for level in self.levels
        ):
            raise ValueError("Dimension hierarchy levels cannot define time_grain.")
        return self


class DatasetSemantics(ContractModel):
    calculated_fields: tuple[DatasetCalculatedField, ...] = Field(default_factory=tuple)
    metrics: tuple[DatasetMetric, ...] = Field(default_factory=tuple)
    relationships: tuple[DatasetRelationship, ...] = Field(default_factory=tuple)
    hierarchies: tuple[DatasetHierarchy, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_unique_names(self) -> "DatasetSemantics":
        for values in (
            self.calculated_fields,
            self.metrics,
            self.relationships,
            self.hierarchies,
        ):
            names = [item.name for item in values]
            if len(names) != len(set(names)):
                raise ValueError("Semantic definition names must be unique within their kind.")
        return self


class DatasetParameter(ContractModel):
    name: NonBlankStr
    data_type: DataType
    required: bool = False
    default: JsonValue = None


class CachePolicy(ContractModel):
    mode: Literal["disabled", "ttl", "scheduled"] = "disabled"
    ttl_seconds: int | None = Field(default=None, ge=1)


class RefreshPolicy(ContractModel):
    mode: Literal["manual", "interval", "cron"] = "manual"
    interval_seconds: int | None = Field(default=None, ge=1)
    cron: str | None = None


class DatasetDefinition(ContractModel):
    schema_version: Literal[1] = 1
    id: NonBlankStr
    name: NonBlankStr
    data_source_id: str | None = None
    query: QueryDefinition
    fields: tuple[DatasetField, ...] = Field(default_factory=tuple)
    profile_overrides: tuple[DatasetFieldOverride, ...] = Field(default_factory=tuple)
    semantics: DatasetSemantics = Field(default_factory=DatasetSemantics)
    parameters: tuple[DatasetParameter, ...] = Field(default_factory=tuple)
    cache: CachePolicy = Field(default_factory=CachePolicy)
    refresh: RefreshPolicy = Field(default_factory=RefreshPolicy)
    max_rows: int = Field(default=5000, ge=1, le=5000)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
