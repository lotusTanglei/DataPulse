import base64
from pathlib import Path

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

    def resolved_sources_dir(self) -> Path:
        return (self.sources_dir or self.data_dir / "sources").resolve()

    def resolved_assets_dir(self) -> Path:
        return (self.assets_dir or self.data_dir / "assets").resolve()

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
