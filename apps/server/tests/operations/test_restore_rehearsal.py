"""A local end-to-end restore drill using the real maintenance CLI and HTTP APIs."""

import base64
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from datapulse.app import create_app
from datapulse.datasource.secrets import SecretBox, SecretEnvelope
from datapulse.settings import Settings
from tests.ecosystem.test_service import archive as plugin_archive
from tests.support.app import SERVER_ROOT, migrate_database
from tests.support.media import image_bytes, wav_bytes

ORIGIN = "http://testserver"
HOST_ORIGIN = "https://host.example.com"
ROWS = [["2026-01", 100], ["2026-02", 200]]
PLUGIN_FILE = "org.example.metrics/1.0.0/files/index.mjs"


def key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


def headers(client: TestClient) -> dict[str, str]:
    return {"Origin": ORIGIN, "X-CSRF-Token": client.cookies["datapulse_csrf"]}


def post(client: TestClient, path: str, *, expected: int = 201, **kwargs):
    response = client.post(path, headers=headers(client), **kwargs)
    assert response.status_code == expected, response.text
    return response.json()


def login(client: TestClient, username: str, password: str) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 204, response.text


def ticket(client: TestClient, api_key: str, screen_id: str):
    return client.post(
        "/api/embed/tickets",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "screen_id": screen_id,
            "allowed_origin": HOST_ORIGIN,
            "parameters": {},
            "mutable_parameters": [],
            "lifetime_seconds": 3600,
        },
    )


def verify_runtime(
    client: TestClient, path: str, resources: dict[str, tuple[bytes, str]], **kwargs
):
    loaded = client.get(path, **kwargs)
    assert loaded.status_code == 200, loaded.text
    components = loaded.json()["document"]["components"]
    assert len(components) == 4
    speaker = next(component for component in components if component["id"] == "speaker")
    assert speaker["type"] == "builtin.digital_human"
    assert speaker["props"]["avatar_asset_id"] in resources
    assert speaker["props"]["audio_asset_id"] == speaker["props"]["recording"]["asset_id"]
    assert speaker["props"]["audio_asset_id"] in resources
    queried = client.post(path + "/query", json={"component_id": "chart"}, **kwargs)
    assert queried.status_code == 200, queried.text
    assert queried.json()["rows"] == ROWS
    for asset_id, (content, mime_type) in resources.items():
        asset = client.get(path + f"/assets/{asset_id}", **kwargs)
        assert asset.status_code == 200
        assert asset.headers["content-type"].startswith(mime_type)
        assert asset.content == content
    plugins = client.get(path + "/plugins", **kwargs)
    assert plugins.status_code == 200, plugins.text
    assert [(item["id"], item["version"]) for item in plugins.json()] == [
        ("org.example.metrics", "1.0.0")
    ]
    plugin = client.get(path + f"/plugins/{PLUGIN_FILE}", **kwargs)
    assert plugin.status_code == 200
    assert plugin.content == b"export default {apiVersion:1};"


def test_cli_clean_restore_rehearsal_and_restart(tmp_path: Path, monkeypatch) -> None:
    # The source and restored deployment receive independently held secrets, never archive files.
    for name in tuple(os.environ):
        if name.startswith("DATAPULSE_"):
            monkeypatch.delenv(name)
    master_key, signing_key, restored_signing_key = key(), key(), key()
    admin_password, editor_password, source_secret = (secrets.token_urlsafe(32) for _ in range(3))
    setup_code = secrets.token_urlsafe(24)
    source = tmp_path / "source"
    source.mkdir()
    migrate_database(source / "datapulse.db")
    (source / "sources").mkdir()
    with sqlite3.connect(source / "sources" / "sales.db") as connection:
        connection.execute("CREATE TABLE sales (month TEXT NOT NULL, amount INTEGER NOT NULL)")
        connection.executemany("INSERT INTO sales VALUES (?, ?)", ROWS)
    settings = Settings(
        environment="test",
        data_dir=source,
        master_key=master_key,
        signing_key=signing_key,
        bootstrap_code_override=setup_code,
        speech_worker_enabled=False,
    )
    media = image_bytes()
    portrait_bytes = image_bytes(color="#243b7a", size=(48, 64))
    audio_bytes = wav_bytes()
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        initialized = client.post(
            "/api/auth/setup",
            json={"code": setup_code, "username": "admin", "password": admin_password},
            headers={"Origin": ORIGIN},
        )
        assert initialized.status_code == 201, initialized.text
        editor = post(
            client,
            "/api/admin/users",
            json={"username": "editor", "password": editor_password, "role": "editor"},
        )
        datasource = post(
            client,
            "/api/admin/datasources",
            json={
                "name": "Rehearsal SQL",
                "config": {"type": "sqlite", "path": "sales.db"},
                "password": source_secret,
            },
        )
        dataset = post(
            client,
            "/api/admin/datasets",
            json={
                "name": "Rehearsal SQL",
                "data_source_id": datasource["id"],
                "sql": "SELECT month, amount FROM sales ORDER BY month",
            },
        )
        file = post(
            client,
            "/api/admin/files",
            files={"file": ("sales.csv", b"month,amount\n2026-01,100\n2026-02,200\n", "text/csv")},
        )
        file_dataset = post(
            client,
            "/api/admin/datasets/files",
            json={"name": "Rehearsal CSV", "file_asset_id": file["id"]},
        )
        asset = post(
            client,
            "/api/admin/assets",
            files={"file": ("poster.png", media, "image/png")},
        )
        portrait = post(
            client,
            "/api/admin/assets",
            files={"file": ("portrait.png", portrait_bytes, "image/png")},
        )
        audio = post(
            client,
            "/api/admin/assets",
            files={"file": ("narration.wav", audio_bytes, "audio/wav")},
        )
        resources = {
            asset["id"]: (media, "image/png"),
            portrait["id"]: (portrait_bytes, "image/png"),
            audio["id"]: (audio_bytes, "audio/wav"),
        }
        post(
            client,
            "/api/admin/ecosystem/packages",
            files={"file": ("metrics.zip", plugin_archive(), "application/zip")},
        )
        screen = post(
            client,
            "/api/admin/screens",
            json={
                "name": "Restore rehearsal",
                "draft_document": {
                    "canvas": {"width": 1920, "height": 1080},
                    "plugin_dependencies": [{"id": "org.example.metrics", "version": "1.0.0"}],
                    "components": [
                        {
                            "id": "chart",
                            "type": "builtin.bar",
                            "frame": {"x": 0, "y": 0, "width": 640, "height": 320},
                            "data_binding": {
                                "chart_spec": {
                                    "dataset_id": dataset["id"],
                                    "dimensions": ["month"],
                                    "measures": [{"field": "amount", "aggregation": "sum"}],
                                    "visual": {"type": "bar"},
                                }
                            },
                        },
                        {
                            "id": "poster",
                            "type": "builtin.image",
                            "frame": {"x": 0, "y": 340, "width": 320, "height": 180},
                            "props": {"asset_id": asset["id"]},
                        },
                        {
                            "id": "custom",
                            "type": "org.example.metric",
                            "frame": {"x": 660, "y": 0, "width": 200, "height": 100},
                            "props": {},
                        },
                        {
                            "id": "speaker",
                            "type": "builtin.digital_human",
                            "frame": {"x": 900, "y": 0, "width": 320, "height": 420},
                            "props": {
                                "avatar_asset_id": portrait["id"],
                                "avatar_kind": "image",
                                "speech_source": "audio",
                                "audio_asset_id": audio["id"],
                                "speech_template": "Local restore rehearsal.",
                                "recording": {
                                    "asset_id": audio["id"],
                                    "sha256": audio["sha256"],
                                    "transcript": "Local restore rehearsal.",
                                    "duration_seconds": audio["media"]["duration_seconds"],
                                },
                            },
                        },
                    ],
                },
            },
        )
        screen_path = f"/api/admin/screens/{screen['id']}"
        published = post(
            client,
            screen_path + "/publish",
            expected=200,
            json={"expected_revision": screen["draft_revision"]},
        )
        for kind, identifier, permission in [
            ("screen", screen["id"], "publish"),
            ("dataset", dataset["id"], "read"),
            ("datasource", datasource["id"], "read"),
            ("asset", asset["id"], "read"),
            ("asset", portrait["id"], "read"),
            ("asset", audio["id"], "read"),
        ]:
            granted = client.put(
                "/api/admin/permissions",
                headers=headers(client),
                json={
                    "resource_type": kind,
                    "resource_id": identifier,
                    "user_id": editor["id"],
                    "permission": permission,
                },
            )
            assert granted.status_code == 200, granted.text
        old_display_key = post(client, screen_path + "/display-key")["key"]
        old_embed_key = post(client, "/api/admin/embed/api-key")["api_key"]
        issued = ticket(client, old_embed_key, screen["id"])
        assert issued.status_code == 201, issued.text
        old_ticket = issued.json()["ticket"]
        old_session = client.cookies["datapulse_session"]

    # No live API/worker or external SQLite writer overlaps maintenance.
    archive_path = tmp_path / "rehearsal.zip"
    command_outputs = []
    cli_environment = {
        **os.environ,
        "DATAPULSE_DATA_DIR": str(source),
        "DATAPULSE_MASTER_KEY": master_key,
        "DATAPULSE_SIGNING_KEY": signing_key,
    }

    def cli(action: str, *args: str):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "datapulse.operations.cli",
                "backup",
                action,
                "--archive",
                str(archive_path),
                *args,
            ],
            cwd=SERVER_ROOT,
            env=cli_environment,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        command_outputs.extend([result.stdout, result.stderr])
        return json.loads(result.stdout)["manifest"]

    started = time.perf_counter()
    manifest = cli("create", "--maintenance")
    backup_seconds = time.perf_counter() - started
    assert manifest["master_key_required"] is True
    assert cli("verify") == manifest
    assert cli("inspect") == manifest
    with zipfile.ZipFile(archive_path) as zipped:
        assert not any(name.endswith((".env", ".key", ".log")) for name in zipped.namelist())
    target = tmp_path / "restored"
    target.mkdir()
    assert list(target.iterdir()) == []
    started = time.perf_counter()
    assert cli("restore", "--target", str(target), "--maintenance") == manifest
    restore_seconds = time.perf_counter() - started
    with sqlite3.connect(target / "datapulse.db") as connection:
        envelope = connection.execute(
            "SELECT secret_envelope FROM data_source WHERE id = ?", (datasource["id"],)
        ).fetchone()[0]
        assert (
            SecretBox(master_key).decrypt(
                datasource["id"], SecretEnvelope.model_validate_json(envelope)
            )
            == source_secret
        )
        for table in ("admin_session", "display_access", "embed_access"):
            assert connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0

    restored_settings = Settings(
        environment="test",
        data_dir=target,
        master_key=master_key,
        signing_key=restored_signing_key,
        speech_worker_enabled=False,
    )
    with TestClient(create_app(restored_settings), base_url=ORIGIN) as client:
        client.cookies.set("datapulse_session", old_session)
        assert client.get("/api/auth/session").status_code == 401
        client.cookies.clear()
        assert (
            client.post(
                f"/api/player/screens/{screen['id']}/session", json={"key": old_display_key}
            ).status_code
            == 401
        )
        assert ticket(client, old_embed_key, screen["id"]).status_code == 401
        assert (
            client.get(
                f"/api/embed/screens/{screen['id']}",
                headers={"Authorization": f"Bearer {old_ticket}", "Origin": HOST_ORIGIN},
            ).status_code
            == 401
        )
        login(client, "admin", admin_password)
        assert (
            client.get(screen_path).json()["published_document"] == published["published_document"]
        )
        for dataset_id in (dataset["id"], file_dataset["id"]):
            result = post(
                client,
                f"/api/admin/datasets/{dataset_id}/preview",
                expected=200,
                json={"parameters": {}},
            )
            assert result["rows"] == ROWS
        for asset_id, (content, _) in resources.items():
            assert client.get(f"/api/admin/assets/{asset_id}").content == content
        assert client.get("/api/admin/ecosystem/packages").json()[0]["version"] == "1.0.0"

        # A second identity must retain its grants and transitive dataset permissions.
        login(client, "editor", editor_password)
        assert client.get("/api/auth/session").json()["role"] == "editor"
        restored = client.get(screen_path)
        assert restored.status_code == 200, restored.text
        edited = client.patch(
            screen_path,
            headers=headers(client),
            json={
                "name": "Restored and edited",
                "draft_document": restored.json()["draft_document"],
                "expected_revision": restored.json()["draft_revision"],
            },
        )
        assert edited.status_code == 200, edited.text
        post(
            client,
            screen_path + "/publish",
            expected=200,
            json={"expected_revision": edited.json()["draft_revision"]},
        )
        login(client, "admin", admin_password)
        display_key = post(client, screen_path + "/display-key")["key"]
        assert (
            client.post(
                f"/api/player/screens/{screen['id']}/session", json={"key": display_key}
            ).status_code
            == 204
        )
        verify_runtime(client, f"/api/player/screens/{screen['id']}", resources)
        embed_key = post(client, "/api/admin/embed/api-key")["api_key"]
        issued = ticket(client, embed_key, screen["id"])
        assert issued.status_code == 201, issued.text
        embed_ticket = issued.json()["ticket"]
        embed_headers = {"Authorization": f"Bearer {embed_ticket}", "Origin": HOST_ORIGIN}
        verify_runtime(
            client, f"/api/embed/screens/{screen['id']}", resources, headers=embed_headers
        )

    # Rebuild the app a second time, proving persisted edits and issued playback credentials work.
    with TestClient(create_app(restored_settings), base_url=ORIGIN) as client:
        login(client, "editor", editor_password)
        persisted = client.get(screen_path)
        assert persisted.status_code == 200, persisted.text
        assert persisted.json()["name"] == "Restored and edited"
        result = post(
            client,
            f"/api/admin/datasets/{dataset['id']}/preview",
            expected=200,
            json={},
        )
        assert result["rows"] == ROWS
        assert (
            client.post(
                f"/api/player/screens/{screen['id']}/session", json={"key": display_key}
            ).status_code
            == 204
        )
        verify_runtime(client, f"/api/player/screens/{screen['id']}", resources)
        verify_runtime(
            client, f"/api/embed/screens/{screen['id']}", resources, headers=embed_headers
        )

    evidence = {
        "scope": "local temporary directories; not target deployment acceptance",
        "backup_seconds": round(backup_seconds, 3),
        "restore_seconds": round(restore_seconds, 3),
        "archive_bytes": archive_path.stat().st_size,
        "uncompressed_bytes": manifest["total_bytes"],
        "archive_members": manifest["member_count"],
        "accounts": 2,
        "datasources": 1,
        "datasets": 2,
        "file_rows": 2,
        "sql_rows": 2,
        "media_assets": 3,
        "digital_human_components": 1,
        "published_screens": 1,
        "plugins": 1,
        "restored_app_starts": 2,
        "independent_master_and_signing_keys": True,
        "old_credentials_revoked": True,
        "editor_grants_preserved": True,
        "display_embed_query_media_plugin_verified_after_restart": True,
        "digital_human_portrait_audio_bytes_verified_after_restart": True,
    }
    report = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
    emitted = "\n".join([*command_outputs, report])
    for secret in (
        master_key,
        signing_key,
        restored_signing_key,
        admin_password,
        editor_password,
        source_secret,
        setup_code,
        old_session,
        old_display_key,
        old_embed_key,
        old_ticket,
        display_key,
        embed_key,
        embed_ticket,
    ):
        assert secret not in emitted
    (tmp_path / "rehearsal-evidence.json").write_text(report + "\n", encoding="utf-8")
    print("RESTORE_REHEARSAL " + report)
