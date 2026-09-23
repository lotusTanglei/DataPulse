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
    # Comma-separated MIME allowlist; `*` keeps the built-in safe formats enabled.
    asset_allowed_mime_types: str = "*"
    asset_max_bytes: int = Field(default=5 * 1024 * 1024, ge=1)
    asset_media_max_bytes: int = Field(default=100 * 1024 * 1024, ge=1)
    asset_total_bytes: int = Field(default=1024 * 1024 * 1024, ge=1)
    asset_total_duration_seconds: float = Field(default=36_000, gt=0)
    asset_max_count: int = Field(default=10_000, ge=1)
    media_max_pixels: int = Field(default=33_554_432, ge=1)
    media_max_duration_seconds: float = Field(default=300, gt=0, le=3600)
    media_timeout_seconds: float = Field(default=30, gt=0, le=300)
    media_concurrency: int = Field(default=2, ge=1, le=8)
    database_url: str | None = None
    bootstrap_code_override: str | None = None
    master_key: str | None = None
    signing_key: str | None = None
    file_max_bytes: int = Field(default=100 * 1024 * 1024, ge=1)
    file_max_rows: int = Field(default=5000, ge=1)
    duckdb_threads: int = Field(default=2, ge=1, le=8)
    duckdb_memory_limit: str = "512MB"
    duckdb_timeout_seconds: int = Field(default=30, ge=1, le=300)
    ai_enabled: bool = False
    ai_base_url: str | None = None
    ai_api_key: str | None = None
    ai_model: str | None = None
    ai_timeout_seconds: int = Field(default=30, ge=1, le=300)
    ai_screen_timeout_seconds: int = Field(default=120, ge=60, le=120)
    ai_max_context_rows: int = Field(default=100, ge=1, le=100)
    ai_max_context_fields: int = Field(default=50, ge=1, le=200)
    ai_max_context_chars: int = Field(default=12_000, ge=1, le=100_000)
    query_global_limit: int = Field(default=4, ge=1)
    query_per_source_limit: int = Field(default=2, ge=1)
    query_acquire_timeout_seconds: float = Field(default=5, ge=0)
    speech_worker_enabled: bool = True
    speech_recover_on_startup: bool = True
    speech_worker_mode: bool = False
    # Optional bearer token for an internal Prometheus scraper. The endpoint
    # remains disabled until an explicit deployment secret is configured.
    metrics_token: str | None = Field(default=None, repr=False)
    upload_scanner_command: tuple[str, ...] = ()
    upload_scanner_timeout_seconds: float = Field(default=30, gt=0, le=300)
    upload_scanner_memory_mb: int = Field(default=1024, ge=64, le=4096)
    upload_scanner_concurrency: int = Field(default=2, ge=1, le=8)

    def resolved_sources_dir(self) -> Path:
        return (self.sources_dir or self.data_dir / "sources").resolve()

    def resolved_assets_dir(self) -> Path:
        return (self.assets_dir or self.data_dir / "assets").resolve()

    def resolved_asset_mime_types(self) -> frozenset[str] | None:
        value = self.asset_allowed_mime_types.strip()
        if value == "*":
            return None
        allowed = frozenset(item.strip().lower() for item in value.split(",") if item.strip())
        if not allowed:
            raise ValueError("DATAPULSE_ASSET_ALLOWED_MIME_TYPES must contain '*' or MIME types.")
        return allowed

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
