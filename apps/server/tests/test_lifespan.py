from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from datapulse.app import create_app
from datapulse.settings import Settings
from tests.support.app import migrate_database


def test_bootstrap_override_is_rejected_outside_test_environment(tmp_path: Path) -> None:
    database_path = tmp_path / "datapulse.db"
    migrate_database(database_path)
    app = create_app(
        Settings(
            environment="development",
            data_dir=tmp_path,
            database_url=f"sqlite+aiosqlite:///{database_path}",
            bootstrap_code_override="must-not-be-used",
        )
    )

    with pytest.raises(RuntimeError, match="test environment"):
        with TestClient(app):
            pass


def test_startup_rejects_unmigrated_metadata_database(tmp_path: Path) -> None:
    database_path = tmp_path / "missing-schema.db"
    app = create_app(
        Settings(
            environment="test",
            data_dir=tmp_path,
            database_url=f"sqlite+aiosqlite:///{database_path}",
            bootstrap_code_override="test-code",
        )
    )

    with pytest.raises(RuntimeError, match="alembic upgrade head"):
        with TestClient(app):
            pass
