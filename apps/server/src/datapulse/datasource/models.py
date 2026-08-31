from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import Field, HttpUrl, SecretStr, field_validator, model_validator

from datapulse.contracts.common import ContractModel, NonBlankStr


class ConnectorType(StrEnum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    HTTP_API = "http_api"


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


class HttpApiConfig(ContractModel):
    """Connection metadata for an HTTP JSON API.

    The credential itself is intentionally not part of this model.  It is stored
    in the datasource secret envelope and provided to the connector at runtime.
    """

    type: Literal[ConnectorType.HTTP_API] = ConnectorType.HTTP_API
    base_url: HttpUrl
    auth_type: Literal["none", "bearer", "api_key", "basic"] = "none"
    api_key_header: NonBlankStr = "X-API-Key"
    username: NonBlankStr | None = None


DatasourceConfig = Annotated[
    SQLiteConfig | PostgreSQLConfig | MySQLConfig | HttpApiConfig,
    Field(discriminator="type"),
]


class DatasourceCreate(ContractModel):
    name: NonBlankStr
    config: DatasourceConfig
    password: SecretStr | None = None

    @model_validator(mode="after")
    def validate_http_api_credentials(self) -> "DatasourceCreate":
        if isinstance(self.config, HttpApiConfig):
            if self.config.auth_type == "basic" and not self.config.username:
                raise ValueError("username is required for basic HTTP API authentication")
            if self.config.auth_type != "none" and self.password is None:
                raise ValueError("password is required for authenticated HTTP API datasources")
        return self


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


class DatasourceTestRequest(ContractModel):
    """Ephemeral connection settings used by the form test action."""

    config: DatasourceConfig
    password: SecretStr | None = None
    datasource_id: str | None = None

    @model_validator(mode="after")
    def validate_http_api_credentials(self) -> "DatasourceTestRequest":
        if isinstance(self.config, HttpApiConfig):
            if self.config.auth_type == "basic" and not self.config.username:
                raise ValueError("username is required for basic HTTP API authentication")
            if (
                self.config.auth_type != "none"
                and self.password is None
                and self.datasource_id is None
            ):
                raise ValueError("password is required for authenticated HTTP API datasources")
        return self


class DatasourceTestResponse(ContractModel):
    status: DatasourceStatus
    latency_ms: int = Field(ge=0)
    error_code: str | None = None


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
