import base64
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.support.app import AppClient, build_test_app


@pytest.fixture
def access_app(tmp_path: Path) -> Iterator[AppClient]:
    with build_test_app(
        tmp_path,
        signing_key=base64.urlsafe_b64encode(b"s" * 32).decode(),
    ) as app_client:
        yield app_client


def setup_admin(app_client: AppClient) -> None:
    response = app_client.client.post(
        "/api/auth/setup",
        json={
            "code": app_client.setup_code,
            "username": "admin",
            "password": "long-enough-password",
        },
        headers={"Origin": app_client.origin},
    )
    assert response.status_code == 201


def mutation_headers(app_client: AppClient) -> dict[str, str]:
    return {
        "Origin": app_client.origin,
        "X-CSRF-Token": app_client.client.cookies["datapulse_csrf"],
    }


def test_admin_can_configure_policy_and_playback_rejects_wrong_origin(
    access_app: AppClient,
) -> None:
    setup_admin(access_app)
    headers = mutation_headers(access_app)
    created = access_app.client.post(
        "/api/admin/screens",
        json={"name": "Restricted screen"},
        headers=headers,
    ).json()
    screen_id = str(created["id"])
    published = access_app.client.post(
        f"/api/admin/screens/{screen_id}/publish",
        json={"expected_revision": 0},
        headers=headers,
    )
    assert published.status_code == 200

    configured = access_app.client.patch(
        f"/api/admin/screens/{screen_id}/access-policy",
        json={"allowed_origins": ["https://safe.example.com"]},
        headers=headers,
    )
    assert configured.status_code == 200
    assert configured.json()["access_policy"] == {
        "allowed_origins": ["https://safe.example.com"],
        "allowed_ips": [],
    }

    key = access_app.client.post(
        f"/api/admin/screens/{screen_id}/display-key",
        headers=headers,
    ).json()["key"]
    denied = access_app.client.post(
        f"/api/player/screens/{screen_id}/session",
        json={"key": key},
        headers={"Origin": "https://evil.example.com"},
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "DISPLAY_ADDRESS_DENIED"

    allowed = access_app.client.post(
        f"/api/player/screens/{screen_id}/session",
        json={"key": key},
        headers={"Origin": "https://safe.example.com"},
    )
    assert allowed.status_code == 204

    api_key_response = access_app.client.post(
        "/api/admin/embed/api-key",
        headers=headers,
    )
    api_key = api_key_response.json()["api_key"]
    wrong_ticket = access_app.client.post(
        "/api/embed/tickets",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "screen_id": screen_id,
            "allowed_origin": "https://evil.example.com",
            "lifetime_seconds": 3600,
        },
    )
    assert wrong_ticket.status_code == 403
    assert wrong_ticket.json()["error"]["code"] == "EMBED_ORIGIN_DENIED"


def test_invalid_policy_is_rejected(access_app: AppClient) -> None:
    setup_admin(access_app)
    headers = mutation_headers(access_app)
    created = access_app.client.post(
        "/api/admin/screens",
        json={"name": "Invalid policy screen"},
        headers=headers,
    ).json()
    response = access_app.client.patch(
        f"/api/admin/screens/{created['id']}/access-policy",
        json={"allowed_ips": ["not-an-ip"]},
        headers=headers,
    )
    assert response.status_code == 422
