from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator

from datapulse.contracts.common import ContractModel, NonBlankStr


class ConnectorType(StrEnum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"


class DatasourceStatus(StrEnum):
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class SQLiteConfig(ContractModel):
    type: Literal[ConnectorType.SQLITE] = ConnectorType.SQLITE
    path: str

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            not value
            or value.strip() != value
            or "\\" in value
            or path.is_absolute()
            or path == PurePosixPath(".")
            or ".." in path.parts
        ):
            raise ValueError("SQLite path must be a relative path inside sources_dir.")
        return path.as_posix()


class PostgreSQLConfig(ContractModel):
    type: Literal[ConnectorType.POSTGRESQL] = ConnectorType.POSTGRESQL
    host: NonBlankStr
    port: int = Field(default=5432, ge=1, le=65535)
    database: NonBlankStr
    username: NonBlankStr
    ssl_mode: Literal[
        "disable",
        "allow",
        "prefer",
        "require",
        "verify-ca",
        "verify-full",
    ] = "prefer"


class MySQLConfig(ContractModel):
    type: Literal[ConnectorType.MYSQL] = ConnectorType.MYSQL
    host: NonBlankStr
    port: int = Field(default=3306, ge=1, le=65535)
    database: NonBlankStr
    username: NonBlankStr
    ssl_mode: Literal["disabled", "preferred", "required"] = "preferred"


DatasourceConfig = Annotated[
    SQLiteConfig | PostgreSQLConfig | MySQLConfig,
    Field(discriminator="type"),
]


class DatasourceCreate(ContractModel):
    name: NonBlankStr
    config: DatasourceConfig
    password: SecretStr | None = None


class DatasourceUpdate(ContractModel):
    name: NonBlankStr | None = None
    config: DatasourceConfig | None = None
    password: SecretStr | None = None
    clear_password: bool = False

    @model_validator(mode="after")
    def validate_secret_patch(self) -> "DatasourceUpdate":
        if self.password is not None and self.clear_password:
            raise ValueError("password and clear_password cannot be used together")
        return self


class DatasourceResponse(ContractModel):
    id: str
    name: NonBlankStr
    config: DatasourceConfig
    status: DatasourceStatus
    has_password: bool
    last_checked_at: datetime | None = None
    last_latency_ms: int | None = None
    last_error_code: str | None = None
    created_at: datetime
    updated_at: datetime
