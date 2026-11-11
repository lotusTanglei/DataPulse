from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = REPOSITORY_ROOT / "apps" / "server"


def migrate_database(database_path: Path) -> None:
    config = Config(str(SERVER_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "head")


def main() -> int:
    os.environ["DATAPULSE_AI_ENABLED"] = "false"

    from datapulse.app import create_app
    from datapulse.settings import Settings

    with TemporaryDirectory(prefix="datapulse-no-ai-") as temporary_dir:
        data_dir = Path(temporary_dir)
        database_path = data_dir / "datapulse.db"
        migrate_database(database_path)
        settings = Settings(
            environment="test",
            data_dir=data_dir,
            database_url=f"sqlite+aiosqlite:///{database_path}",
            bootstrap_code_override="no-ai-verification",
            ai_enabled=False,
        )
        app = create_app(settings)

        with TestClient(app) as client:
            health = client.get("/api/health")
            auth_status = client.get("/api/auth/status")
            ai_status = client.get("/api/admin/ai/status")

        paths = set(app.openapi()["paths"])
        checks = {
            "health": health.status_code == 200,
            "auth_status": auth_status.status_code == 200
            and auth_status.json().get("ai_enabled") is False,
            "ai_route_hidden": ai_status.status_code == 404,
            "dataset_route_available": "/api/admin/datasets" in paths,
            "screen_route_available": "/api/admin/screens" in paths,
        }
        ai_loaded = any(
            name == "datapulse.ai" or name.startswith("datapulse.ai.") for name in sys.modules
        )
        result = {
            "status": "ok" if all(checks.values()) and not ai_loaded else "failed",
            "ai_loaded": ai_loaded,
            "checks": checks,
        }
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
