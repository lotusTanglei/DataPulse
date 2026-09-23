from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from datapulse.ai.gateway import AiGateway
from datapulse.app import create_app
from datapulse.settings import Settings
from datapulse.worker import worker_settings
from datapulse.operations.maintenance import MaintenanceBusy, maintenance_lease
from tests.support.app import migrate_database


def test_screen_query_bursts_wait_for_a_limiter_slot_by_default() -> None:
    settings = Settings()

    assert settings.query_global_limit == 4
    assert settings.query_per_source_limit == 2
    assert settings.query_acquire_timeout_seconds == 5


def test_asset_mime_allowlist_is_parsed_from_deployment_settings() -> None:
    assert Settings(
        asset_allowed_mime_types="image/png, audio/wav"
    ).resolved_asset_mime_types() == frozenset({"image/png", "audio/wav"})
    assert Settings(asset_allowed_mime_types="*").resolved_asset_mime_types() is None
    with pytest.raises(ValueError, match="ASSET_ALLOWED_MIME_TYPES"):
        Settings(asset_allowed_mime_types=" ").resolved_asset_mime_types()


def test_standalone_worker_settings_do_not_recover_queued_api_tasks() -> None:
    settings = worker_settings()
    assert settings.speech_worker_enabled is True
    assert settings.speech_recover_on_startup is False
    assert settings.speech_worker_mode is True


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


def test_lifespan_closes_ai_gateway(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database_path = tmp_path / "datapulse.db"
    migrate_database(database_path)
    closed: list[AiGateway] = []

    async def close(gateway: AiGateway) -> None:
        closed.append(gateway)

    monkeypatch.setattr(AiGateway, "aclose", close)
    app = create_app(
        Settings(
            environment="test",
            data_dir=tmp_path,
            database_url=f"sqlite+aiosqlite:///{database_path}",
            bootstrap_code_override="test-code",
        )
    )

    with TestClient(app):
        assert app.state.ai_gateway.health().status == "unconfigured"

    assert closed == [app.state.ai_gateway]


def test_running_instance_excludes_offline_backup_and_releases_after_shutdown(tmp_path):
    database_path = tmp_path / "datapulse.db"
    migrate_database(database_path)
    app = create_app(Settings(environment="test", data_dir=tmp_path, bootstrap_code_override="fixture"))
    with TestClient(app):
        with pytest.raises(MaintenanceBusy):
            with maintenance_lease(tmp_path):
                pass
    with maintenance_lease(tmp_path):
        with pytest.raises(MaintenanceBusy):
            with TestClient(app):
                pass
