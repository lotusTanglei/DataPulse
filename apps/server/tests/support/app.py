from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from alembic import command
from alembic.config import Config
from fastapi import Depends
from fastapi.testclient import TestClient

from datapulse.app import create_app
from datapulse.auth.dependencies import require_admin, require_csrf
from datapulse.metadata import AdminAccount
from datapulse.settings import Settings

SERVER_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class AppClient:
    client: TestClient
    setup_code: str
    origin: str
    database_path: Path


def migrate_database(database_path: Path) -> None:
    config = Config(str(SERVER_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "head")


@contextmanager
def build_test_app(
    tmp_path: Path,
    *,
    setup_code: str = "test-setup-code",
    app_version: str = "0.1.0",
    signing_key: str | None = None,
    static_dir: Path | None = None,
) -> Iterator[AppClient]:
    database_path = tmp_path / "datapulse.db"
    migrate_database(database_path)
    settings = Settings(
        environment="test",
        data_dir=tmp_path,
        database_url=f"sqlite+aiosqlite:///{database_path}",
        bootstrap_code_override=setup_code,
        app_version=app_version,
        signing_key=signing_key,
        static_dir=static_dir,
    )
    app = create_app(settings)

    @app.get("/api/admin/probe")
    async def get_probe(
        admin: Annotated[AdminAccount, Depends(require_admin)],
    ) -> dict[str, str]:
        return {"username": admin.username}

    @app.post("/api/admin/probe", dependencies=[Depends(require_csrf)])
    async def post_probe() -> dict[str, bool]:
        return {"ok": True}

    origin = "http://testserver"
    with TestClient(app, base_url=origin) as client:
        yield AppClient(
            client=client,
            setup_code=setup_code,
            origin=origin,
            database_path=database_path,
        )
