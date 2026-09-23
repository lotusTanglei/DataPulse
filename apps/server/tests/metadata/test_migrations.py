import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

SERVER_ROOT = Path(__file__).resolve().parents[2]


def run_alembic_upgrade(database_path: Path) -> None:
    config = Config(str(SERVER_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "head")


def inspect_sqlite_tables(database_path: Path) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


def inspect_sqlite_columns(database_path: Path, table: str) -> dict[str, tuple[str, bool]]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1]: (row[2], not bool(row[3])) for row in rows}


def inspect_sqlite_unique_indexes(database_path: Path, table: str) -> set[tuple[str, ...]]:
    with sqlite3.connect(database_path) as connection:
        indexes = connection.execute(f"PRAGMA index_list({table})").fetchall()
        return {
            tuple(row[2] for row in connection.execute(f"PRAGMA index_info({index[1]})").fetchall())
            for index in indexes
            if index[2]
        }


def test_upgrade_head_creates_expected_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "migration.db"

    run_alembic_upgrade(database_path)

    assert {
        "system_state",
        "admin_account",
        "admin_session",
        "data_source",
        "dataset",
        "file_asset",
        "query_run",
        "screen",
        "screen_asset",
        "display_access",
        "embed_access",
        "digital_human_provider",
        "speech_plan",
        "speech_task",
        "digital_human_usage",
        "digital_human_settings",
        "digital_human_provider_health",
        "digital_human_audit",
        "alembic_version",
    } <= inspect_sqlite_tables(database_path)
    columns = inspect_sqlite_columns(database_path, "screen")
    assert columns["draft_document"] == ("JSON", False)
    assert columns["published_document"] == ("JSON", True)
    assert columns["draft_revision"] == ("INTEGER", False)
    assert columns["created_at"] == ("DATETIME", False)
    assert columns["updated_at"] == ("DATETIME", False)
    assert ("name",) in inspect_sqlite_unique_indexes(database_path, "screen")
    dataset_columns = inspect_sqlite_columns(database_path, "dataset")
    assert dataset_columns["data_source_id"] == ("VARCHAR(36)", True)
    file_columns = inspect_sqlite_columns(database_path, "file_asset")
    assert file_columns["format"] == ("VARCHAR(16)", False)
    assert file_columns["storage_path"] == ("TEXT", False)
    assert file_columns["fields_json"] == ("JSON", False)
    display_columns = inspect_sqlite_columns(database_path, "display_access")
    assert display_columns["key_hash"] == ("VARCHAR(64)", False)
    assert display_columns["key_version"] == ("INTEGER", False)
    embed_columns = inspect_sqlite_columns(database_path, "embed_access")
    assert embed_columns["api_key_hash"] == ("VARCHAR(64)", False)
    assert embed_columns["key_version"] == ("INTEGER", False)
    provider_columns = inspect_sqlite_columns(database_path, "digital_human_provider")
    assert provider_columns["cost_per_minute"] == ("FLOAT", False)
    assert provider_columns["consecutive_failures"] == ("INTEGER", False)
    assert provider_columns["circuit_open_until"] == ("DATETIME", True)
    assert provider_columns["provider_version"] == ("VARCHAR(120)", False)
    plan_columns = inspect_sqlite_columns(database_path, "speech_plan")
    assert plan_columns["provider_version"] == ("VARCHAR(120)", False)
    assert plan_columns["rate"] == ("FLOAT", False)
    assert plan_columns["pitch"] == ("FLOAT", False)
    assert plan_columns["volume"] == ("FLOAT", False)
    usage_columns = inspect_sqlite_columns(database_path, "digital_human_usage")
    assert usage_columns["estimated_cost"] == ("FLOAT", False)
    assert usage_columns["synthesis_attempts"] == ("INTEGER", False)
    assert usage_columns["synthesis_failures"] == ("INTEGER", False)
    assert usage_columns["synthesis_total_ms"] == ("FLOAT", False)
    settings_columns = inspect_sqlite_columns(database_path, "digital_human_settings")
    assert settings_columns["ai_enabled"] == ("BOOLEAN", False)
    assert settings_columns["ai_model"] == ("VARCHAR(120)", False)
    assert settings_columns["ai_context_limit"] == ("INTEGER", False)
    assert settings_columns["data_retention_days"] == ("INTEGER", False)


def test_upgrade_head_uses_configured_data_dir(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "datapulse.db"
    config = Config(str(SERVER_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", "sqlite:///:memory:")
    monkeypatch.setenv("DATAPULSE_DATA_DIR", str(tmp_path))

    command.upgrade(config, "head")

    assert "alembic_version" in inspect_sqlite_tables(database_path)


def test_speech_metrics_migration_preserves_legacy_usage(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy-speech-metrics.db"
    config = Config(str(SERVER_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    previous = "0017_digital_human_content_governance"
    command.upgrade(config, previous)
    legacy = ("usage-1", "2026-09-10 00:00:00", "provider-1", 4, 2, 1, 12.5, 1, 2.5)
    columns = (
        "id, period_start, provider_id, task_count, succeeded_count, failed_count, "
        "generated_seconds, cached_count, estimated_cost"
    )
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            f"INSERT INTO digital_human_usage ({columns}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            legacy,
        )
    command.upgrade(config, "0018_speech_metrics_timing")
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            f"SELECT {columns} FROM digital_human_usage"
        ).fetchone() == legacy
        assert connection.execute(
            "SELECT synthesis_attempts, synthesis_failures, synthesis_total_ms "
            "FROM digital_human_usage"
        ).fetchone() == (0, 0, 0)
        connection.execute(
            "UPDATE digital_human_usage SET synthesis_attempts=3, "
            "synthesis_failures=1, synthesis_total_ms=123.5"
        )
    command.downgrade(config, previous)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            f"SELECT {columns} FROM digital_human_usage"
        ).fetchone() == legacy
    assert "synthesis_total_ms" not in inspect_sqlite_columns(database_path, "digital_human_usage")
    command.upgrade(config, "head")
    assert "synthesis_total_ms" in inspect_sqlite_columns(database_path, "digital_human_usage")


def test_media_migration_preserves_legacy_assets_through_upgrade_and_downgrade(tmp_path) -> None:
    database_path = tmp_path / "legacy-media.db"
    config = Config(str(SERVER_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "0008_screen_access_policy")
    legacy = (
        "existing-asset",
        "image",
        "image/png",
        "a" * 64,
        123,
        str(tmp_path / "existing.png"),
        "2026-09-01 00:00:00",
    )
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO screen_asset "
            "(id, asset_type, mime_type, sha256, size_bytes, storage_path, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            legacy,
        )
    command.upgrade(config, "0009_screen_asset_media")
    with sqlite3.connect(database_path) as connection:
        assert (
            connection.execute(
                "SELECT id, asset_type, mime_type, sha256, size_bytes, storage_path, created_at "
                "FROM screen_asset"
            ).fetchone()
            == legacy
        )
        assert connection.execute(
            "SELECT name, original_name, family_id, version, media_json FROM screen_asset"
        ).fetchone() == ("existing-asset", "existing-asset", "existing-asset", 1, "{}")
        indexes = {row[1] for row in connection.execute("PRAGMA index_list(screen_asset)")}
        assert "ix_screen_asset_sha256" in indexes
    assert ("family_id", "version") in inspect_sqlite_unique_indexes(database_path, "screen_asset")
    command.downgrade(config, "0008_screen_access_policy")
    with sqlite3.connect(database_path) as connection:
        assert (
            connection.execute(
                "SELECT id, asset_type, mime_type, sha256, size_bytes, storage_path, created_at "
                "FROM screen_asset"
            ).fetchone()
            == legacy
        )
    command.upgrade(config, "head")
    assert "family_id" in inspect_sqlite_columns(database_path, "screen_asset")
