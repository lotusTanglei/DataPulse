import base64
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATAPULSE_", extra="ignore")

    app_name: str = "DataPulse"
    app_version: str = "0.1.0"
    environment: str = "development"
    static_dir: Path | None = None
    data_dir: Path = Path("data")
    sources_dir: Path | None = None
    assets_dir: Path | None = None
    database_url: str | None = None
    bootstrap_code_override: str | None = None
    master_key: str | None = None
    signing_key: str | None = None
    file_max_bytes: int = Field(default=100 * 1024 * 1024, ge=1)
    file_max_rows: int = Field(default=5000, ge=1)
    duckdb_threads: int = Field(default=2, ge=1, le=8)
    duckdb_memory_limit: str = "512MB"
    duckdb_timeout_seconds: int = Field(default=30, ge=1, le=300)
    query_global_limit: int = Field(default=4, ge=1)
    query_per_source_limit: int = Field(default=2, ge=1)
    query_acquire_timeout_seconds: float = Field(default=5, ge=0)

    def resolved_sources_dir(self) -> Path:
        return (self.sources_dir or self.data_dir / "sources").resolve()

    def resolved_assets_dir(self) -> Path:
        return (self.assets_dir or self.data_dir / "assets").resolve()

    def resolved_files_dir(self) -> Path:
        return (self.data_dir / "files").resolve()

    def signing_key_bytes(self) -> bytes | None:
        if self.signing_key is None:
            return None
        padding = "=" * (-len(self.signing_key) % 4)
        try:
            decoded = base64.b64decode(
                f"{self.signing_key}{padding}",
                altchars=b"-_",
                validate=True,
            )
        except (TypeError, ValueError) as error:
            raise ValueError("DATAPULSE_SIGNING_KEY must be URL-safe Base64.") from error
        if len(decoded) != 32:
            raise ValueError("DATAPULSE_SIGNING_KEY must decode to exactly 32 bytes.")
        return decoded
