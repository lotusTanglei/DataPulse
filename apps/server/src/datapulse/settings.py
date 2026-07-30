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

    def resolved_sources_dir(self) -> Path:
        return (self.sources_dir or self.data_dir / "sources").resolve()

    def resolved_assets_dir(self) -> Path:
        return (self.assets_dir or self.data_dir / "assets").resolve()
