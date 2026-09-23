import base64
import io
import json
import zipfile
from contextlib import closing

from fastapi.testclient import TestClient

from tests.support.app import build_test_app


def plugin_package(version="1.0.0"):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(
                {
                    "id": "org.example.delivery",
                    "version": version,
                    "compatible_api": ">=1,<2",
                    "name": "Delivery",
                    "entry": "index.mjs",
                    "components": [
                        {
                            "type": "org.example.delivery.card",
                            "name": "Card",
                            "category": "指标",
                            "property_schema": {"type": "object"},
                            "data_schema": {},
                        }
                    ],
                }
            ),
        )
        archive.writestr("index.mjs", "export default {apiVersion:1,components:{}};")
    return output.getvalue()


def test_plugin_publication_and_document_scoped_delivery(tmp_path):
    signing = base64.urlsafe_b64encode(b"s" * 32).decode()
    static = tmp_path / "web"
    static.mkdir()
    (static / "index.html").write_text("<html>fixture</html>")
    with build_test_app(tmp_path, signing_key=signing, static_dir=static) as app:
        client = app.client
        assert (
            client.post(
                "/api/auth/setup",
                json={"code": app.setup_code, "username": "admin", "password": "fixture-password"},
                headers={"Origin": app.origin},
            ).status_code
            == 201
        )
        headers = {"Origin": app.origin, "X-CSRF-Token": client.cookies["datapulse_csrf"]}
        app.app.state.ecosystem_service.install(plugin_package())
        app.app.state.ecosystem_service.install(plugin_package("2.0.0"))
        doc = {
            "canvas": {"width": 1920, "height": 1080},
            "plugin_dependencies": [{"id": "org.example.delivery", "version": "1.0.0"}],
            "components": [
                {
                    "id": "card",
                    "type": "org.example.delivery.card",
                    "frame": {"x": 0, "y": 0, "width": 200, "height": 100},
                    "props": {},
                }
            ],
        }
        created = client.post(
            "/api/admin/screens",
            json={"name": "Plugin delivery", "draft_document": doc},
            headers=headers,
        )
        assert created.status_code == 201, created.text
        sid = created.json()["id"]
        published = client.post(
            f"/api/admin/screens/{sid}/publish", json={"expected_revision": 0}, headers=headers
        )
        assert published.status_code == 200, published.text
        key = client.post(f"/api/admin/screens/{sid}/display-key", headers=headers).json()["key"]
        with closing(TestClient(app.app, base_url=app.origin)) as player:
            root = f"/api/player/screens/{sid}/plugins"
            assert player.get(root).status_code == 401
            assert (
                player.post(f"/api/player/screens/{sid}/session", json={"key": key}).status_code
                == 204
            )
            descriptors = player.get(root)
            assert descriptors.status_code == 200
            assert [p["version"] for p in descriptors.json()] == ["1.0.0"]
            entry = player.get(f"{root}/org.example.delivery/1.0.0/files/index.mjs")
            assert entry.status_code == 200
            assert "javascript" in entry.headers["content-type"]
            assert entry.headers["cache-control"] == "no-store"
            assert (
                player.get(f"{root}/org.example.delivery/2.0.0/files/index.mjs").status_code == 404
            )
        api_key = client.post("/api/admin/embed/api-key", headers=headers).json()["api_key"]
        ticket = client.post(
            "/api/embed/tickets",
            json={"screen_id": sid, "allowed_origin": "https://host.example"},
            headers={"Authorization": f"Bearer {api_key}"},
        ).json()["ticket"]
        page = client.get(
            f"/embed/{sid}", params={"ticket": ticket}, headers={"Referer": "https://host.example/"}
        )
        assert page.status_code == 200
        assert "script-src 'self' blob:;" in page.headers["content-security-policy"]
        root = f"/api/embed/screens/{sid}/plugins"
        assert client.get(root).status_code == 401
        authorized = {"Authorization": f"Bearer {ticket}", "Origin": "https://host.example"}
        descriptors = client.get(root, headers=authorized)
        assert descriptors.status_code == 200
        assert descriptors.headers["access-control-allow-origin"] == "https://host.example"
        assert (
            client.get(
                f"{root}/org.example.delivery/1.0.0/files/index.mjs", headers=authorized
            ).status_code
            == 200
        )
        assert (
            client.get(
                f"{root}/org.example.delivery/2.0.0/files/index.mjs", headers=authorized
            ).status_code
            == 404
        )
