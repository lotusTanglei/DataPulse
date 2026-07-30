from pydantic import Field

from datapulse.contracts.common import ContractModel, JsonValue


class ValidatedQuery(ContractModel):
    sql: str
    dialect: str
    query_hash: str


class QueryRequest(ContractModel):
    sql: str
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    max_rows: int = Field(default=1000, ge=1, le=5000)
    timeout_seconds: int = Field(default=30, ge=1, le=300)


class QueryColumn(ContractModel):
    name: str
    data_type: str


class QueryResult(ContractModel):
    request_id: str
    columns: tuple[QueryColumn, ...]
    rows: tuple[tuple[JsonValue, ...], ...]
    row_count: int = Field(ge=0)
    truncated: bool
    duration_ms: int = Field(ge=0)
