from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, HttpUrl

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


class RestQuery(ContractModel):
    kind: Literal["rest"] = "rest"
    method: Literal["GET", "POST"] = "GET"
    url: HttpUrl


QueryDefinition = Annotated[
    TableQuery | SqlQuery | FileQuery | RestQuery,
    Field(discriminator="kind"),
]


class DatasetField(ContractModel):
    name: NonBlankStr
    data_type: DataType


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
    parameters: tuple[DatasetParameter, ...] = Field(default_factory=tuple)
    cache: CachePolicy = Field(default_factory=CachePolicy)
    refresh: RefreshPolicy = Field(default_factory=RefreshPolicy)
    max_rows: int = Field(default=5000, ge=1, le=5000)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
