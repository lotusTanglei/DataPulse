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


def test_upgrade_head_creates_expected_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "migration.db"

    run_alembic_upgrade(database_path)

    assert {
        "system_state",
        "admin_account",
        "admin_session",
        "data_source",
        "dataset",
        "query_run",
        "alembic_version",
    } <= inspect_sqlite_tables(database_path)


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
