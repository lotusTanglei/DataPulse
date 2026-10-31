from __future__ import annotations

import base64
import os
import secrets
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient


REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
SERVER_ROOT = REPOSITORY_ROOT / "apps" / "server"
SAMPLE_DATA = REPOSITORY_ROOT / "fixtures" / "demo" / "business.csv"
DEMO_SCREEN_NAME = "DataPulse 经营分析示例"
DEMO_DATASET_NAME = "DataPulse 经营样例"
DEMO_HOST_ORIGIN = "https://demo.example.com"


class HttpResponse(Protocol):
    status_code: int
    text: str

    def json(self) -> Any: ...


class HttpClient(Protocol):
    cookies: Any

    def get(self, url: str, **kwargs: Any) -> HttpResponse: ...

    def post(self, url: str, **kwargs: Any) -> HttpResponse: ...

    def patch(self, url: str, **kwargs: Any) -> HttpResponse: ...


def _secret() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")


def _read_environment(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if not separator or not name:
            raise ValueError(f"Invalid environment entry in {path}.")
        values[name] = value
    return values


def write_demo_environment(path: Path, *, http_port: int = 8000) -> dict[str, str]:
    if path.exists():
        os.chmod(path, 0o600)
        return _read_environment(path)
    if not 1 <= http_port <= 65535:
        raise ValueError("The demo HTTP port must be between 1 and 65535.")
    values = {
        "DATAPULSE_MASTER_KEY": _secret(),
        "DATAPULSE_SIGNING_KEY": _secret(),
        "DATAPULSE_HTTP_PORT": str(http_port),
        "DATAPULSE_DEMO_ADMIN_USERNAME": "admin",
        "DATAPULSE_DEMO_ADMIN_PASSWORD": secrets.token_urlsafe(24),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write("\n".join(f"{name}={value}" for name, value in values.items()) + "\n")
    return values


def build_compose_command(environment_path: Path, project_name: str) -> list[str]:
    return [
        "docker",
        "compose",
        "--env-file",
        str(environment_path),
        "--project-name",
        project_name,
        "up",
        "--detach",
        "--build",
        "--wait",
        "datapulse",
    ]


def build_demo_document(dataset_id: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "canvas": {
            "width": 1920,
            "height": 1080,
            "background": {"color": "#08111f"},
        },
        "theme": {
            "id": "datapulse-dark",
            "tokens": {"screen_accent": "#26d9c1"},
        },
        "components": [
            {
                "id": "sales-trend",
                "type": "builtin.line",
                "frame": {"x": 40, "y": 120, "width": 1180, "height": 820},
                "props": {"title": "区域销售趋势", "empty_text": "暂无数据"},
                "data_binding": {
                    "chart_spec": {
                        "schema_version": 1,
                        "dataset_id": dataset_id,
                        "dimensions": ["日期"],
                        "measures": [{"field": "销售额", "aggregation": "sum"}],
                        "sort": [{"field": "日期", "direction": "asc"}],
                        "visual": {"type": "line", "title": "区域销售趋势"},
                    }
                },
            },
            {
                "id": "sales-speaker",
                "type": "builtin.digital_human",
                "frame": {"x": 1260, "y": 120, "width": 620, "height": 820},
                "props": {
                    "name": "经营播报员",
                    "role": "经营分析",
                    "speech_template": "当前首日销售额 {{sales.amount | number}} 元。",
                    "speech_source": "browser",
                    "muted": True,
                },
                "data_binding": {
                    "source": "components",
                    "variables": [
                        {
                            "name": "sales.amount",
                            "component_id": "sales-trend",
                            "field": "销售额",
                            "row": 0,
                        }
                    ],
                },
            },
        ],
    }


def _require(response: HttpResponse, status: int) -> dict[str, Any]:
    if response.status_code != status:
        raise RuntimeError(
            f"Delivery API returned {response.status_code}, expected {status}: {response.text}"
        )
    if status == 204:
        return {}
    body = response.json()
    if not isinstance(body, dict):
        raise RuntimeError("Delivery API returned an unexpected response body.")
    return body


def _mutation_headers(client: HttpClient, origin: str) -> dict[str, str]:
    csrf = client.cookies.get("datapulse_csrf")
    if not csrf:
        raise RuntimeError("The delivery session does not contain a CSRF token.")
    return {"Origin": origin, "X-CSRF-Token": str(csrf)}


def authenticate_demo(
    client: HttpClient,
    *,
    origin: str,
    username: str,
    password: str,
    setup_code: str | None,
) -> None:
    status = _require(client.get("/api/auth/status"), 200)
    if status.get("initialized") is False:
        if not setup_code:
            raise RuntimeError("The fresh deployment setup code was not found in container logs.")
        _require(
            client.post(
                "/api/auth/setup",
                headers={"Origin": origin},
                json={"code": setup_code, "username": username, "password": password},
            ),
            201,
        )
        return
    response = client.post(
        "/api/auth/login",
        headers={"Origin": origin},
        json={"username": username, "password": password},
    )
    _require(response, 204)


def seed_demo(
    client: HttpClient,
    *,
    origin: str,
    sample_path: Path = SAMPLE_DATA,
) -> dict[str, str]:
    headers = _mutation_headers(client, origin)
    datasets_response = client.get("/api/admin/datasets")
    if datasets_response.status_code != 200:
        raise RuntimeError(datasets_response.text)
    datasets = datasets_response.json()
    dataset = next((item for item in datasets if item.get("name") == DEMO_DATASET_NAME), None)
    if dataset is None:
        uploaded = _require(
            client.post(
                "/api/admin/files",
                headers=headers,
                files={"file": (sample_path.name, sample_path.read_bytes(), "text/csv")},
            ),
            201,
        )
        dataset = _require(
            client.post(
                "/api/admin/datasets/files",
                headers=headers,
                json={"name": DEMO_DATASET_NAME, "file_asset_id": uploaded["id"]},
            ),
            201,
        )

    screens_response = client.get("/api/admin/screens")
    if screens_response.status_code != 200:
        raise RuntimeError(screens_response.text)
    screens = screens_response.json()
    summary = next((item for item in screens if item.get("name") == DEMO_SCREEN_NAME), None)
    if summary is None:
        screen = _require(
            client.post(
                "/api/admin/screens",
                headers=headers,
                json={
                    "name": DEMO_SCREEN_NAME,
                    "description": "仓库固定样例生成的发布与嵌入演示。",
                    "draft_document": build_demo_document(str(dataset["id"])),
                },
            ),
            201,
        )
    else:
        screen = _require(client.get(f"/api/admin/screens/{summary['id']}"), 200)
    if screen.get("published_document") is None:
        screen = _require(
            client.post(
                f"/api/admin/screens/{screen['id']}/publish",
                headers=headers,
                json={"expected_revision": screen["draft_revision"]},
            ),
            200,
        )
    return {"dataset_id": str(dataset["id"]), "screen_id": str(screen["id"])}


def _migrate_database(database_path: Path) -> None:
    config = Config(str(SERVER_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "head")


def run_clean_delivery_rehearsal(data_dir: Path) -> dict[str, object]:
    from datapulse.app import create_app
    from datapulse.settings import Settings

    data_dir.mkdir(parents=True, exist_ok=True)
    database_path = data_dir / "datapulse.db"
    _migrate_database(database_path)
    setup_code = secrets.token_urlsafe(24)
    settings = Settings(
        environment="test",
        data_dir=data_dir,
        database_url=f"sqlite+aiosqlite:///{database_path}",
        bootstrap_code_override=setup_code,
        master_key=_secret(),
        signing_key=_secret(),
        ai_enabled=False,
        speech_worker_enabled=False,
    )
    app = create_app(settings)
    origin = "http://testserver"
    checks: dict[str, bool] = {}
    sample_rows = 0
    with TestClient(app, base_url=origin) as client:
        authenticate_demo(
            client,
            origin=origin,
            username="admin",
            password="delivery-demo-password",
            setup_code=setup_code,
        )
        identifiers = seed_demo(client, origin=origin)
        dataset_id = identifiers["dataset_id"]
        screen_id = identifiers["screen_id"]
        headers = _mutation_headers(client, origin)

        auth_status = _require(client.get("/api/auth/status"), 200)
        checks["ai_disabled"] = (
            auth_status.get("ai_enabled") is False
            and client.get("/api/admin/ai/status").status_code == 404
        )
        profile = _require(client.get(f"/api/admin/datasets/{dataset_id}/profile"), 200)
        checks["dataset_profiled"] = bool(profile.get("fields"))
        preview = _require(
            client.post(
                f"/api/admin/datasets/{dataset_id}/preview",
                headers=headers,
                json={"parameters": {}},
            ),
            200,
        )
        sample_rows = int(preview.get("row_count", 0))
        screen = _require(client.get(f"/api/admin/screens/{screen_id}"), 200)
        checks["draft_created"] = len(screen["draft_document"]["components"]) == 2
        speaker = next(
            item
            for item in screen["published_document"]["components"]
            if item["id"] == "sales-speaker"
        )
        checks["static_speech_fallback"] = (
            speaker["props"]["speech_source"] == "browser"
            and not speaker["props"].get("audio_asset_id")
            and speaker["data_binding"]["variables"][0]["component_id"] == "sales-trend"
        )
        checks["published"] = screen.get("published_document") is not None

        display = _require(
            client.post(f"/api/admin/screens/{screen_id}/display-key", headers=headers), 201
        )
        _require(
            client.post(
                f"/api/player/screens/{screen_id}/session", json={"key": display["key"]}
            ),
            204,
        )
        player = _require(client.get(f"/api/player/screens/{screen_id}"), 200)
        player_query = _require(
            client.post(
                f"/api/player/screens/{screen_id}/query",
                json={"component_id": "sales-trend", "parameters": {}},
            ),
            200,
        )
        checks["standalone_playback"] = (
            player["document"] == screen["published_document"]
            and player_query.get("row_count", 0) > 0
        )

        embed_key = _require(client.post("/api/admin/embed/api-key", headers=headers), 201)
        ticket = _require(
            client.post(
                "/api/embed/tickets",
                headers={"Authorization": f"Bearer {embed_key['api_key']}"},
                json={
                    "screen_id": screen_id,
                    "allowed_origin": DEMO_HOST_ORIGIN,
                    "parameters": {},
                    "mutable_parameters": [],
                    "lifetime_seconds": 3600,
                },
            ),
            201,
        )
        bearer = {
            "Authorization": f"Bearer {ticket['ticket']}",
            "Origin": DEMO_HOST_ORIGIN,
        }
        embedded = _require(client.get(f"/api/embed/screens/{screen_id}", headers=bearer), 200)
        checks["embed_playback"] = embedded["document"] == screen["published_document"]
        _require(
            client.patch(
                f"/api/admin/screens/{screen_id}/access-policy",
                headers=headers,
                json={"allowed_origins": ["https://denied.example.com"]},
            ),
            200,
        )
        denied = client.get(f"/api/embed/screens/{screen_id}", headers=bearer)
        checks["embed_permission_denied"] = (
            denied.status_code == 403
            and denied.json().get("error", {}).get("code") == "EMBED_ORIGIN_DENIED"
        )

    return {
        "status": "ok" if sample_rows > 0 and all(checks.values()) else "failed",
        "sample_rows": sample_rows,
        "checks": checks,
    }


__all__: Sequence[str] = (
    "DEMO_HOST_ORIGIN",
    "REPOSITORY_ROOT",
    "SAMPLE_DATA",
    "authenticate_demo",
    "build_compose_command",
    "build_demo_document",
    "run_clean_delivery_rehearsal",
    "seed_demo",
    "write_demo_environment",
)
