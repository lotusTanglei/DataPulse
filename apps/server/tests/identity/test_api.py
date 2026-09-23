import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.auth.test_api import setup_admin
from tests.support.app import AppClient, build_test_app

PASSWORD = "identity-test-password"


@pytest.fixture
def system(tmp_path: Path) -> Iterator[AppClient]:
    with build_test_app(tmp_path) as value:
        setup_admin(value)
        yield value


def headers(client: TestClient) -> dict[str, str]:
    return {"Origin": "http://testserver", "X-CSRF-Token": client.cookies["datapulse_csrf"]}


def create_user(system: AppClient, username: str = "editor", role: str = "editor") -> dict:
    response = system.client.post(
        "/api/admin/users",
        json={
            "username": username,
            "password": PASSWORD,
            "role": role,
        },
        headers=headers(system.client),
    )
    assert response.status_code == 201, response.text
    return response.json()


def login(system: AppClient, username: str, password: str = PASSWORD) -> TestClient:
    client = TestClient(system.app, base_url=system.origin)
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
        headers={"Origin": system.origin},
    )
    assert response.status_code == 204, response.text
    return client


def test_account_lifecycle_and_redacted_audit(system: AppClient) -> None:
    account = create_user(system)
    assert account["id"] != "admin"
    assert account["active"] is True
    assert set(account) == {"id", "username", "role", "active", "created_at", "updated_at"}
    editor = login(system, "editor")
    assert editor.get("/api/auth/session").json() == {
        "id": account["id"],
        "username": "editor",
        "role": "editor",
    }
    assert editor.get("/api/admin/users").status_code == 403
    assert editor.get("/api/admin/probe").status_code == 403
    changed = system.client.patch(
        f"/api/admin/users/{account['id']}", json={"role": "viewer"}, headers=headers(system.client)
    )
    assert changed.status_code == 200
    assert editor.get("/api/auth/session").status_code == 401
    editor = login(system, "editor")
    reset = system.client.patch(
        f"/api/admin/users/{account['id']}",
        json={"password": "new-identity-password"},
        headers=headers(system.client),
    )
    assert reset.status_code == 200
    assert editor.get("/api/auth/session").status_code == 401
    editor = login(system, "editor", "new-identity-password")
    disabled = system.client.patch(
        f"/api/admin/users/{account['id']}", json={"active": False}, headers=headers(system.client)
    )
    assert disabled.status_code == 200
    assert editor.get("/api/auth/session").status_code == 401
    assert (
        editor.post(
            "/api/auth/login",
            json={"username": "editor", "password": "new-identity-password"},
            headers={"Origin": system.origin},
        ).status_code
        == 401
    )
    audit = system.client.get("/api/admin/identity/audit")
    assert audit.status_code == 200
    assert {event["action"] for event in audit.json()} >= {
        "user.create",
        "user.update",
        "user.password_reset",
    }
    assert "password_hash" not in audit.text and PASSWORD not in audit.text
    assert "new-identity-password" not in audit.text


@pytest.mark.parametrize("patch", [{"active": False}, {"role": "viewer"}])
def test_last_active_admin_is_preserved(system: AppClient, patch: dict) -> None:
    response = system.client.patch(
        "/api/admin/users/admin", json=patch, headers=headers(system.client)
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "IDENTITY_LAST_ADMIN"
    assert system.client.get("/api/auth/session").status_code == 200


def test_account_contracts_csrf_and_duplicate_name(system: AppClient) -> None:
    assert (
        system.client.post(
            "/api/admin/users", json={"username": "x", "password": PASSWORD, "role": "editor"}
        ).status_code
        == 403
    )
    for patch in (
        {"role": "superadmin"},
        {"active": "false"},
        {"password_hash": "bad"},
        {"role": None},
        {},
    ):
        assert (
            system.client.patch(
                "/api/admin/users/admin", json=patch, headers=headers(system.client)
            ).status_code
            == 422
        )
    create_user(system)
    duplicate = system.client.post(
        "/api/admin/users",
        json={"username": "editor", "password": PASSWORD, "role": "viewer"},
        headers=headers(system.client),
    )
    assert duplicate.status_code == 409


def create_screen(client: TestClient, name: str) -> dict:
    result = client.post("/api/admin/screens", json={"name": name}, headers=headers(client))
    assert result.status_code == 201, result.text
    return result.json()


def grant(
    system: AppClient, resource_type: str, resource_id: str, user: dict, permission: str = "read"
):
    return system.client.put(
        "/api/admin/permissions",
        json={
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user_id": user["id"],
            "permission": permission,
        },
        headers=headers(system.client),
    )


def test_private_screens_grants_role_ceiling_and_revocation(system: AppClient) -> None:
    account = create_user(system)
    viewer_account = create_user(system, "viewer", "viewer")
    editor = login(system, "editor")
    viewer = login(system, "viewer")
    screen = create_screen(system.client, "Admin private")
    screen_id = screen["id"]
    assert editor.get("/api/admin/screens").json() == []
    hidden = editor.get(f"/api/admin/screens/{screen_id}")
    missing = editor.get("/api/admin/screens/missing")
    assert hidden.status_code == missing.status_code == 404
    assert hidden.json()["error"]["code"] == missing.json()["error"]["code"]
    assert (
        editor.patch(
            f"/api/admin/screens/{screen_id}", json={"name": "stolen"}, headers=headers(editor)
        ).status_code
        == 404
    )
    assert grant(system, "screen", screen_id, account).status_code == 200
    assert editor.get(f"/api/admin/screens/{screen_id}").status_code == 200
    assert len(editor.get("/api/admin/screens").json()) == 1
    assert (
        editor.post(
            f"/api/admin/screens/{screen_id}/publish",
            json={"expected_revision": 0},
            headers=headers(editor),
        ).status_code
        == 404
    )
    assert grant(system, "screen", screen_id, viewer_account, "write").status_code == 200
    assert viewer.get(f"/api/admin/screens/{screen_id}").status_code == 200
    assert (
        viewer.patch(
            f"/api/admin/screens/{screen_id}", json={"name": "stolen"}, headers=headers(viewer)
        ).status_code
        == 404
    )
    assert (
        viewer.post(
            "/api/admin/screens", json={"name": "blocked"}, headers=headers(viewer)
        ).status_code
        == 403
    )
    owned = create_screen(editor, "Editor private")
    assert editor.get(f"/api/admin/screens/{owned['id']}").status_code == 200
    assert viewer.get(f"/api/admin/screens/{owned['id']}").status_code == 404
    assert (
        editor.put(
            "/api/admin/permissions",
            json={
                "resource_type": "screen",
                "resource_id": owned["id"],
                "user_id": viewer_account["id"],
                "permission": "read",
            },
            headers=headers(editor),
        ).status_code
        == 200
    )
    assert viewer.get(f"/api/admin/screens/{owned['id']}").status_code == 200
    revoked = system.client.delete(
        f"/api/admin/permissions/screen/{screen_id}/{account['id']}", headers=headers(system.client)
    )
    assert revoked.status_code == 204
    assert editor.get(f"/api/admin/screens/{screen_id}").status_code == 404
    assert editor.get("/api/admin/identity/directory").status_code == 200


def test_reference_injection_denied_before_data_execution(system: AppClient) -> None:
    account = create_user(system)
    editor = login(system, "editor")
    file = system.client.post(
        "/api/admin/files",
        files={"file": ("secret.csv", b"value\n42\n", "text/csv")},
        headers=headers(system.client),
    ).json()
    dataset = system.client.post(
        "/api/admin/datasets/files",
        json={"name": "secret", "file_asset_id": file["id"]},
        headers=headers(system.client),
    )
    assert dataset.status_code == 201, dataset.text
    dataset_id = dataset.json()["id"]
    denied = editor.post(
        "/api/admin/datasets/files",
        json={"name": "stolen", "file_asset_id": file["id"]},
        headers=headers(editor),
    )
    assert denied.status_code == 404
    for path, payload in [
        ("/api/admin/ai/analyze", {"question": "secret", "dataset_ids": [dataset_id]}),
        (f"/api/admin/datasets/{dataset_id}/preview", {}),
    ]:
        assert editor.post(path, json=payload, headers=headers(editor)).status_code == 404
    assert grant(system, "dataset", dataset_id, account).status_code == 200
    assert editor.get("/api/admin/datasets").json() == []
    assert (
        editor.post(
            f"/api/admin/datasets/{dataset_id}/preview", json={}, headers=headers(editor)
        ).status_code
        == 404
    )
    assert grant(system, "file", file["id"], account).status_code == 200
    assert [item["id"] for item in editor.get("/api/admin/datasets").json()] == [dataset_id]
    assert (
        editor.post(
            f"/api/admin/datasets/{dataset_id}/preview", json={}, headers=headers(editor)
        ).status_code
        == 200
    )
    assert (
        system.client.delete(
            f"/api/admin/permissions/file/{file['id']}/{account['id']}",
            headers=headers(system.client),
        ).status_code
        == 204
    )
    assert (
        editor.post(
            f"/api/admin/datasets/{dataset_id}/preview", json={}, headers=headers(editor)
        ).status_code
        == 404
    )
    assert editor.get("/api/admin/datasets").json() == []


def test_editor_can_compile_recompile_and_request_ai_edits_for_visible_datasets(
    system: AppClient,
) -> None:
    account = create_user(system)
    editor = login(system, "editor")
    file = system.client.post(
        "/api/admin/files",
        files={"file": ("sales.csv", "amount\n42\n", "text/csv")},
        headers=headers(system.client),
    ).json()
    dataset = system.client.post(
        "/api/admin/datasets/files",
        json={"name": "Shared sales", "file_asset_id": file["id"]},
        headers=headers(system.client),
    ).json()
    assert grant(system, "file", file["id"], account).status_code == 200
    assert grant(system, "dataset", dataset["id"], account).status_code == 200
    plan = {
        "title": "Sales",
        "audience": "Operator",
        "narrative": "Show total sales.",
        "dataset_ids": [dataset["id"]],
        "regions": [{"id": "summary", "kind": "summary"}],
        "widgets": [
            {
                "id": "total",
                "title": "Total",
                "intent": "Show total sales",
                "region_id": "summary",
                "dataset_id": dataset["id"],
                "chart_type": "kpi",
                "measures": [{"field": "amount", "aggregation": "sum"}],
            }
        ],
    }

    compiled = editor.post(
        "/api/admin/screens/plan/compile",
        json={"plan": plan},
        headers=headers(editor),
    )
    assert compiled.status_code == 200, compiled.text
    next_plan = {**plan, "widgets": [{**plan["widgets"][0], "title": "Sales total"}]}
    recompiled = editor.post(
        "/api/admin/screens/plan/recompile",
        json={
            "previous_plan": plan,
            "plan": next_plan,
            "document": compiled.json()["document"],
            "affected_region_ids": ["summary"],
        },
        headers=headers(editor),
    )
    assert recompiled.status_code == 200, recompiled.text

    ai_edit = editor.post(
        "/api/admin/ai/screen/edit",
        json={
            "question": "Use a bar chart",
            "plan": next_plan,
            "document": recompiled.json()["document"],
            "affected_region_ids": ["summary"],
        },
        headers=headers(editor),
    )
    assert ai_edit.status_code == 503, ai_edit.text
    assert ai_edit.json()["error"]["code"] == "AI_NOT_CONFIGURED"


def test_editor_cannot_register_or_test_arbitrary_server_sqlite_files(system: AppClient) -> None:
    account = create_user(system)
    editor = login(system, "editor")
    sources = system.database_path.parent / "sources"
    sources.mkdir(exist_ok=True)
    for name in ("payroll.db", "public.db"):
        with sqlite3.connect(sources / name) as connection:
            connection.execute("CREATE TABLE payroll (private_salary INTEGER)")
            connection.execute("INSERT INTO payroll VALUES (98765)")
    private = system.client.post(
        "/api/admin/datasources",
        headers=headers(system.client),
        json={"name": "Private payroll", "config": {"type": "sqlite", "path": "payroll.db"}},
    )
    assert private.status_code == 201, private.text
    shared = system.client.post(
        "/api/admin/datasources",
        headers=headers(system.client),
        json={"name": "Public", "config": {"type": "sqlite", "path": "public.db"}},
    )
    assert shared.status_code == 201, shared.text
    assert grant(system, "datasource", shared.json()["id"], account, "write").status_code == 200
    assert editor.get(f"/api/admin/datasources/{private.json()['id']}").status_code == 404
    config = {"type": "sqlite", "path": "payroll.db"}
    for method, path, payload in [
        ("POST", "/api/admin/datasources", {"name": "Alias", "config": config}),
        ("POST", "/api/admin/datasources/test", {"config": config}),
        (
            "POST",
            "/api/admin/datasources/test",
            {"config": config, "datasource_id": shared.json()["id"]},
        ),
        ("PATCH", f"/api/admin/datasources/{shared.json()['id']}", {"config": config}),
    ]:
        response = editor.request(method, path, json=payload, headers=headers(editor))
        assert response.status_code == 403, (method, path, response.text)
    queried = editor.post(
        f"/api/admin/datasources/{shared.json()['id']}/query",
        json={"sql": "SELECT private_salary FROM payroll"},
        headers=headers(editor),
    )
    assert queried.status_code == 200, queried.text
    assert queried.json()["rows"] == [[98765]]
    tested = editor.post(
        f"/api/admin/datasources/{shared.json()['id']}/test", headers=headers(editor)
    )
    assert tested.status_code == 200, tested.text
    renamed = editor.patch(
        f"/api/admin/datasources/{shared.json()['id']}",
        json={"name": "Shared renamed"},
        headers=headers(editor),
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["config"] == {"type": "sqlite", "path": "public.db"}
    private_dataset = system.client.post(
        "/api/admin/datasets",
        headers=headers(system.client),
        json={
            "name": "Private payroll dataset",
            "data_source_id": private.json()["id"],
            "sql": "SELECT private_salary FROM payroll",
        },
    )
    assert private_dataset.status_code == 201, private_dataset.text
    dataset_id = private_dataset.json()["id"]
    assert grant(system, "dataset", dataset_id, account).status_code == 200
    assert editor.get("/api/admin/datasets").json() == []
    assert grant(system, "datasource", private.json()["id"], account).status_code == 200
    assert [item["id"] for item in editor.get("/api/admin/datasets").json()] == [dataset_id]
    assert (
        system.client.delete(
            f"/api/admin/permissions/datasource/{private.json()['id']}/{account['id']}",
            headers=headers(system.client),
        ).status_code
        == 204
    )
    assert editor.get("/api/admin/datasets").json() == []


def test_write_grant_cannot_change_access_policy_through_screen_patch(system: AppClient) -> None:
    account = create_user(system)
    editor = login(system, "editor")
    screen = create_screen(system.client, "publication protected")
    assert grant(system, "screen", screen["id"], account, "write").status_code == 200
    response = editor.patch(
        f"/api/admin/screens/{screen['id']}", json={"access_policy": {}}, headers=headers(editor)
    )
    assert response.status_code == 404


def test_asset_bytes_and_duplicate_upload_remain_private(system: AppClient) -> None:
    import io

    from PIL import Image

    image = io.BytesIO()
    Image.new("RGB", (2, 2), color="red").save(image, format="PNG")
    content = image.getvalue()
    account = create_user(system)
    editor = login(system, "editor")
    uploaded = system.client.post(
        "/api/admin/assets",
        files={"file": ("secret.png", content, "image/png")},
        headers=headers(system.client),
    )
    assert uploaded.status_code == 201, uploaded.text
    asset_id = uploaded.json()["id"]
    assert editor.get(f"/api/admin/assets/{asset_id}").status_code == 404
    assert editor.get("/api/admin/assets").json() == []
    duplicate = editor.post(
        "/api/admin/assets",
        files={"file": ("mine.png", content, "image/png")},
        headers=headers(editor),
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] != asset_id
    assert duplicate.json()["name"] == "mine.png"
    assert editor.get(f"/api/admin/assets/{duplicate.json()['id']}").status_code == 200
    assert grant(system, "asset", asset_id, account).status_code == 200
    downloaded = editor.get(f"/api/admin/assets/{asset_id}")
    assert downloaded.status_code == 200
    assert "no-store" in downloaded.headers["cache-control"]
    assert (
        system.client.delete(
            f"/api/admin/permissions/asset/{asset_id}/{account['id']}",
            headers=headers(system.client),
        ).status_code
        == 204
    )
    assert editor.get(f"/api/admin/assets/{asset_id}").status_code == 404


def test_two_editors_conflict_and_publish_permissions(system: AppClient) -> None:
    first = create_user(system, "first")
    second = create_user(system, "second")
    first_client = login(system, "first")
    second_client = login(system, "second")
    screen = create_screen(system.client, "Shared draft")
    identifier = screen["id"]
    assert grant(system, "screen", identifier, first, "write").status_code == 200
    assert grant(system, "screen", identifier, second, "publish").status_code == 200
    body = {"draft_document": screen["draft_document"], "expected_revision": 0}
    saved = first_client.patch(
        f"/api/admin/screens/{identifier}", json=body, headers=headers(first_client)
    )
    assert saved.status_code == 200
    stale = second_client.patch(
        f"/api/admin/screens/{identifier}", json=body, headers=headers(second_client)
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "SCREEN_REVISION_CONFLICT"
    assert (
        first_client.post(
            f"/api/admin/screens/{identifier}/display-key", headers=headers(first_client)
        ).status_code
        == 404
    )
    assert (
        second_client.post(
            f"/api/admin/screens/{identifier}/publish",
            json={"expected_revision": 1},
            headers=headers(second_client),
        ).status_code
        == 200
    )
    assert (
        second_client.post(
            f"/api/admin/screens/{identifier}/display-key", headers=headers(second_client)
        ).status_code
        == 201
    )
    assert (
        second_client.get(
            f"/api/admin/permissions?resource_type=screen&resource_id={identifier}"
        ).status_code
        == 404
    )


def test_screen_document_references_are_checked_for_save_and_runtime(system: AppClient) -> None:
    account = create_user(system)
    editor = login(system, "editor")
    screen = create_screen(editor, "Editor draft")
    document = screen["draft_document"]
    document["components"] = [
        {
            "id": "image-1",
            "type": "builtin.image",
            "frame": {"x": 0, "y": 0, "width": 100, "height": 100},
            "props": {"asset_id": "private-asset"},
        }
    ]
    for path, body in [
        ("/api/admin/screens", {"name": "Bad create", "draft_document": document}),
        (
            f"/api/admin/screens/{screen['id']}",
            {"draft_document": document, "expected_revision": 0},
        ),
        ("/api/admin/screens/query-document", {"document": document, "component_id": "image-1"}),
        (
            "/api/admin/ai/edit",
            {"question": "describe", "document": document, "selected_component_ids": ["image-1"]},
        ),
    ]:
        response = editor.request(
            "PATCH" if path.endswith(screen["id"]) else "POST",
            path,
            json=body,
            headers=headers(editor),
        )
        assert response.status_code == 404, response.text
    assert account["id"]


def test_sensitive_system_routes_remain_admin_only(system: AppClient) -> None:
    create_user(system)
    editor = login(system, "editor")
    for path in [
        "/api/admin/digital-human/providers",
        "/api/admin/digital-human/settings",
        "/api/admin/identity/audit",
    ]:
        response = editor.get(path)
        assert response.status_code == 403, (path, response.text)


def test_concurrent_admin_demotions_keep_one_active_admin(system: AppClient) -> None:
    from concurrent.futures import ThreadPoolExecutor

    account = create_user(system, "second-admin", "admin")
    first_client = login(system, "admin", "long-enough-password")
    second_client = login(system, "second-admin")

    def demote(client: TestClient, identifier: str) -> int:
        return client.patch(
            f"/api/admin/users/{identifier}", json={"role": "editor"}, headers=headers(client)
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(demote, first_client, "admin"),
            pool.submit(demote, second_client, account["id"]),
        ]
        assert sorted(future.result() for future in futures) == [200, 409]


def test_read_screen_checks_published_snapshot_references(system: AppClient) -> None:
    import json
    import sqlite3

    account = create_user(system)
    editor = login(system, "editor")
    screen = create_screen(system.client, "Published reference")
    document = screen["draft_document"]
    document["components"] = [
        {
            "id": "image",
            "type": "builtin.image",
            "frame": {"x": 0, "y": 0, "width": 100, "height": 100},
            "props": {"asset_id": "private-published-asset"},
        }
    ]
    with sqlite3.connect(system.database_path) as connection:
        connection.execute(
            "UPDATE screen SET published_document=? WHERE id=?",
            (json.dumps(document), screen["id"]),
        )
    assert grant(system, "screen", screen["id"], account).status_code == 200
    assert editor.get(f"/api/admin/screens/{screen['id']}").status_code == 404


@pytest.mark.parametrize("content_type", [None, "application/vnd.api+json", "Application/JSON"])
def test_json_media_types_cannot_bypass_reference_or_publish_checks(
    system: AppClient, content_type: str | None
) -> None:
    import json

    account = create_user(system)
    editor = login(system, "editor")
    screen = create_screen(system.client, "Media type protected")
    assert grant(system, "screen", screen["id"], account, "write").status_code == 200
    request_headers = headers(editor)
    if content_type:
        request_headers["Content-Type"] = content_type
    changed = editor.patch(
        f"/api/admin/screens/{screen['id']}",
        content=json.dumps({"access_policy": {}}),
        headers=request_headers,
    )
    assert changed.status_code == 404


def test_asset_pagination_and_usage_count_only_visible_resources(system: AppClient) -> None:
    from tests.support.media import image_bytes

    create_user(system)
    editor = login(system, "editor")
    own = editor.post(
        "/api/admin/assets",
        files={"file": ("own.png", image_bytes(color="red"), "image/png")},
        headers=headers(editor),
    )
    assert own.status_code == 201
    for color in ["blue", "green"]:
        assert (
            system.client.post(
                "/api/admin/assets",
                files={"file": (f"{color}.png", image_bytes(color=color), "image/png")},
                headers=headers(system.client),
            ).status_code
            == 201
        )
    listed = editor.get("/api/admin/assets?limit=1")
    assert [item["id"] for item in listed.json()] == [own.json()["id"]]
    usage = editor.get("/api/admin/assets/usage")
    assert usage.status_code == 200
    assert usage.json()["asset_count"] == 1
    assert system.client.get("/api/admin/assets/usage").json()["asset_count"] == 3


def test_read_shared_datasource_cannot_reuse_credentials_with_alternate_config(
    system: AppClient,
) -> None:
    account = create_user(system)
    editor = login(system, "editor")
    source = system.client.post(
        "/api/admin/datasources",
        json={
            "name": "Read only connector",
            "config": {
                "type": "http_api",
                "base_url": "https://source.example.com",
                "auth_type": "none",
            },
        },
        headers=headers(system.client),
    )
    assert source.status_code == 201, source.text
    identifier = source.json()["id"]
    assert grant(system, "datasource", identifier, account, "read").status_code == 200
    response = editor.post(
        "/api/admin/datasources/test",
        json={
            "datasource_id": identifier,
            "config": {
                "type": "http_api",
                "base_url": "https://alternate.example.com",
                "auth_type": "none",
            },
        },
        headers=headers(editor),
    )
    assert response.status_code == 404
