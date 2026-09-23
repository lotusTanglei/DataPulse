import sqlite3

from tests.identity.test_api import create_screen, create_user, grant, headers, login, system
from tests.support.app import AppClient

# Reuse the real application fixture rather than a mocked authorization layer.
__all__ = ["system"]
BASE = "/api/admin/digital-human"


def configured_provider(
    system: AppClient, identifier: str = "tts-enabled", *, enabled: bool = True
) -> None:
    with sqlite3.connect(system.database_path) as connection:
        connection.execute(
            "INSERT INTO digital_human_provider "
            "(id,name,provider_type,base_url,secret_envelope,default_voice,language,enabled,"
            "cost_per_minute,provider_version,consecutive_failures,created_at,updated_at) "
            "VALUES (?,?, 'openai-compatible','https://private.internal/tts','secret-marker',"
            "'alloy','zh-CN',?,0,'v1',0,'2026-01-01','2026-01-01')",
            (identifier, identifier, enabled),
        )


def speaker_screen(client, name: str) -> dict:
    screen = create_screen(client, name)
    document = screen["draft_document"]
    document["components"] = [
        {
            "id": "speaker",
            "type": "builtin.digital_human",
            "frame": {"x": 0, "y": 0, "width": 100, "height": 100},
            "props": {"speech_template": "Hello"},
        }
    ]
    response = client.patch(
        f"/api/admin/screens/{screen['id']}",
        json={"draft_document": document, "expected_revision": 0},
        headers=headers(client),
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_editor_provider_directory_and_scoped_speech_tasks(system: AppClient) -> None:
    account = create_user(system)
    other_account = create_user(system, "other")
    editor = login(system, "editor")
    other = login(system, "other")
    configured_provider(system)
    configured_provider(system, "tts-disabled", enabled=False)
    directory = editor.get(f"{BASE}/provider-directory")
    assert directory.status_code == 200
    assert directory.json() == [
        {"id": "tts-enabled", "name": "tts-enabled", "language": "zh-CN", "default_voice": "alloy"}
    ]
    assert "private.internal" not in directory.text and "secret-marker" not in directory.text
    assert editor.get(f"{BASE}/providers").status_code == 403
    screen = speaker_screen(system.client, "Shared speech")
    assert grant(system, "screen", screen["id"], account, "write").status_code == 200
    assert grant(system, "screen", screen["id"], other_account, "write").status_code == 200
    payload = {
        "screen_id": screen["id"],
        "component_id": "speaker",
        "text": "Hello",
        "provider_id": "tts-enabled",
        "voice": "alloy",
    }
    preview = editor.post(f"{BASE}/plans/preview", json=payload, headers=headers(editor))
    assert preview.status_code == 200, preview.text
    plan_id = preview.json()["id"]
    assert other.post(f"{BASE}/plans/{plan_id}/tasks", headers=headers(other)).status_code == 404
    assert (
        editor.post(
            f"{BASE}/plans/{plan_id}/tasks?approved=true", headers=headers(editor)
        ).status_code
        == 403
    )
    queued = editor.post(f"{BASE}/plans/{plan_id}/tasks", headers=headers(editor))
    assert queued.status_code == 201, queued.text
    task_id = queued.json()["id"]
    assert editor.get(f"{BASE}/tasks/{task_id}").status_code == 200
    assert other.get(f"{BASE}/tasks/{task_id}").status_code == 404
    assert editor.delete(f"{BASE}/tasks/{task_id}", headers=headers(editor)).status_code == 200
    assert (
        system.client.delete(
            f"/api/admin/permissions/screen/{screen['id']}/{account['id']}",
            headers=headers(system.client),
        ).status_code
        == 204
    )
    assert editor.get(f"{BASE}/tasks/{task_id}").status_code == 404
    assert (
        editor.post(f"{BASE}/plans/preview", json=payload, headers=headers(editor)).status_code
        == 404
    )


def test_editor_cannot_forge_speech_scope_or_select_disabled_provider(system: AppClient) -> None:
    create_user(system)
    editor = login(system, "editor")
    configured_provider(system)
    configured_provider(system, "tts-disabled", enabled=False)
    screen = speaker_screen(editor, "Owned speech")
    base = {
        "screen_id": screen["id"],
        "component_id": "speaker",
        "text": "Hello",
        "provider_id": "tts-enabled",
        "voice": "alloy",
    }
    for patch in [
        {"screen_id": "missing"},
        {"component_id": "missing"},
        {"provider_id": "tts-disabled"},
        {"provider_id": "missing"},
        {"provider_id": ""},
    ]:
        response = editor.post(
            f"{BASE}/plans/preview", json={**base, **patch}, headers=headers(editor)
        )
        assert response.status_code == 404, response.text
    assert editor.get(f"{BASE}/provider-directory/tts-disabled/voices").status_code == 404


def test_completed_preview_audio_is_readable_only_by_its_creator(system: AppClient) -> None:
    from tests.support.media import wav_bytes

    create_user(system)
    create_user(system, "other")
    editor = login(system, "editor")
    other = login(system, "other")
    configured_provider(system)
    screen = speaker_screen(editor, "Generated speech")
    preview = editor.post(
        f"{BASE}/plans/preview",
        json={
            "screen_id": screen["id"],
            "component_id": "speaker",
            "text": "Hello",
            "provider_id": "tts-enabled",
            "voice": "alloy",
        },
        headers=headers(editor),
    )
    assert preview.status_code == 200, preview.text
    queued = editor.post(f"{BASE}/plans/{preview.json()['id']}/tasks", headers=headers(editor))
    assert queued.status_code == 201, queued.text
    asset = system.client.post(
        "/api/admin/assets",
        files={"file": ("speech.wav", wav_bytes(), "audio/wav")},
        headers=headers(system.client),
    )
    assert asset.status_code == 201, asset.text
    asset_id = asset.json()["id"]
    with sqlite3.connect(system.database_path) as connection:
        connection.execute(
            "UPDATE speech_task SET status='succeeded', asset_id=? WHERE id=?",
            (asset_id, queued.json()["id"]),
        )
    assert editor.get(f"/api/admin/assets/{asset_id}").status_code == 404
    polled = editor.get(f"{BASE}/tasks/{queued.json()['id']}")
    assert polled.status_code == 200 and polled.json()["asset_id"] == asset_id
    assert editor.get(f"/api/admin/assets/{asset_id}").status_code == 200
    assert other.get(f"/api/admin/assets/{asset_id}").status_code == 404


def test_invalid_speech_scope_is_neutral_and_does_not_crash(system: AppClient) -> None:
    create_user(system)
    editor = login(system, "editor")
    response = editor.post(
        f"{BASE}/plans/preview",
        json={
            "screen_id": ["invalid", "extra"],
            "component_id": "speaker",
            "text": "Hello",
            "provider_id": "tts-enabled",
            "voice": "alloy",
        },
        headers=headers(editor),
    )
    assert response.status_code == 404
