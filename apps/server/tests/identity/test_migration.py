import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

from tests.support.app import SERVER_ROOT


def test_identity_migration_preserves_account_sessions_and_owns_legacy_resources(
    tmp_path: Path,
) -> None:
    database = tmp_path / "legacy.db"
    config = Config(str(SERVER_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "0019_speech_plan_voice_settings")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO admin_account "
            "(id, username, password_hash, password_changed_at, created_at, updated_at) "
            "VALUES ('admin', 'legacy-admin', 'unchanged-hash', "
            "'2026-01-01', '2026-01-01', '2026-01-01')"
        )
        connection.execute(
            "INSERT INTO admin_session "
            "(id,admin_id,csrf_token_hash,created_at,expires_at,last_seen_at) "
            "VALUES ('old-session','admin','csrf','2026-01-01','2030-01-01','2026-01-01')"
        )
        connection.execute(
            "INSERT INTO screen "
            "(id,name,description,draft_document,draft_revision,"
            "access_policy_json,created_at,updated_at) "
            "VALUES ('screen-1','legacy screen','','{}',0,'{}','2026-01-01','2026-01-01')"
        )
    command.upgrade(config, "0020_identity")
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT id,username,password_hash,role,active FROM admin_account"
        ).fetchone() == ("admin", "legacy-admin", "unchanged-hash", "admin", 1)
        assert connection.execute("SELECT id,admin_id FROM admin_session").fetchone() == (
            "old-session",
            "admin",
        )
        assert connection.execute(
            "SELECT resource_type,resource_id,owner_id FROM resource_ownership"
        ).fetchall() == [("screen", "screen-1", "admin")]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    command.downgrade(config, "0019_speech_plan_voice_settings")
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT password_hash FROM admin_account").fetchone() == (
            "unchanged-hash",
        )
