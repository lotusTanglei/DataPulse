import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from tests.support.app import AppClient, build_test_app


@pytest.fixture
def app_client(tmp_path: Path) -> Iterator[AppClient]:
    with build_test_app(tmp_path) as client:
        yield client


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


def test_setup_login_session_logout_flow(app_client: AppClient) -> None:
    assert app_client.client.get("/api/auth/status").json() == {"initialized": False}

    setup = app_client.client.post(
        "/api/auth/setup",
        json={
            "code": app_client.setup_code,
            "username": "admin",
            "password": "long-enough-password",
        },
        headers={"Origin": app_client.origin},
    )

    assert setup.status_code == 201
    cookies = setup.headers.get_list("set-cookie")
    assert any("datapulse_session=" in cookie and "HttpOnly" in cookie for cookie in cookies)
    assert any("datapulse_csrf=" in cookie and "HttpOnly" not in cookie for cookie in cookies)
    assert all("SameSite=lax" in cookie and "Path=/" in cookie for cookie in cookies)
    assert app_client.client.get("/api/auth/status").json() == {"initialized": True}
    assert app_client.client.get("/api/auth/session").json() == {"username": "admin"}
    assert app_client.client.get("/api/admin/probe").json() == {"username": "admin"}

    csrf = app_client.client.cookies["datapulse_csrf"]
    logout = app_client.client.post(
        "/api/auth/logout",
        headers={"X-CSRF-Token": csrf, "Origin": app_client.origin},
    )

    assert logout.status_code == 204
    assert app_client.client.get("/api/auth/session").status_code == 401

    login = app_client.client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "long-enough-password"},
        headers={"Origin": app_client.origin},
    )
    assert login.status_code == 204
    assert app_client.client.get("/api/auth/session").json() == {"username": "admin"}


def test_setup_rejects_wrong_code_wrong_origin_and_second_setup(
    app_client: AppClient,
) -> None:
    wrong_origin = app_client.client.post(
        "/api/auth/setup",
        json={
            "code": app_client.setup_code,
            "username": "admin",
            "password": "long-enough-password",
        },
        headers={"Origin": "https://attacker.example"},
    )
    assert wrong_origin.status_code == 403
    assert wrong_origin.json()["error"]["code"] == "AUTH_ORIGIN_INVALID"

    wrong_code = app_client.client.post(
        "/api/auth/setup",
        json={
            "code": "wrong-code",
            "username": "admin",
            "password": "long-enough-password",
        },
        headers={"Origin": app_client.origin},
    )
    assert wrong_code.status_code == 400
    assert wrong_code.json()["error"]["code"] == "AUTH_INVALID_SETUP_CODE"

    setup_admin(app_client)
    second = app_client.client.post(
        "/api/auth/setup",
        json={
            "code": app_client.setup_code,
            "username": "second",
            "password": "another-long-password",
        },
        headers={"Origin": app_client.origin},
    )
    assert second.status_code == 404
    assert second.json()["error"]["code"] == "AUTH_SETUP_NOT_AVAILABLE"


def test_setup_rejects_expired_code(app_client: AppClient) -> None:
    with sqlite3.connect(app_client.database_path) as connection:
        connection.execute(
            "UPDATE system_state SET setup_code_expires_at = ? WHERE id = 1",
            ("2000-01-01 00:00:00.000000",),
        )

    response = app_client.client.post(
        "/api/auth/setup",
        json={
            "code": app_client.setup_code,
            "username": "admin",
            "password": "long-enough-password",
        },
        headers={"Origin": app_client.origin},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "AUTH_INVALID_SETUP_CODE"


def test_login_is_uniformly_rejected_then_rate_limited(app_client: AppClient) -> None:
    setup_admin(app_client)
    app_client.client.cookies.clear()

    for _ in range(5):
        response = app_client.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong-password"},
            headers={"Origin": app_client.origin},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"

    limited = app_client.client.post(
        "/api/auth/login",
        json={"username": "missing", "password": "wrong-password"},
        headers={"Origin": app_client.origin},
    )
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "AUTH_RATE_LIMITED"


def test_admin_routes_require_session_and_csrf(app_client: AppClient) -> None:
    assert app_client.client.get("/api/admin/probe").status_code == 401

    setup_admin(app_client)
    missing = app_client.client.post(
        "/api/admin/probe",
        headers={"Origin": app_client.origin},
    )
    assert missing.status_code == 403
    assert missing.json()["error"]["code"] == "AUTH_CSRF_INVALID"

    mismatched = app_client.client.post(
        "/api/admin/probe",
        headers={"Origin": app_client.origin, "X-CSRF-Token": "wrong"},
    )
    assert mismatched.status_code == 403
    assert mismatched.json()["error"]["code"] == "AUTH_CSRF_INVALID"

    csrf = app_client.client.cookies["datapulse_csrf"]
    success = app_client.client.post(
        "/api/admin/probe",
        headers={"Origin": app_client.origin, "X-CSRF-Token": csrf},
    )
    assert success.status_code == 200


def test_password_change_keeps_current_session_and_revokes_old_password(
    app_client: AppClient,
) -> None:
    setup_admin(app_client)
    csrf = app_client.client.cookies["datapulse_csrf"]

    changed = app_client.client.patch(
        "/api/auth/password",
        json={
            "current_password": "long-enough-password",
            "new_password": "new-long-enough-password",
        },
        headers={"Origin": app_client.origin, "X-CSRF-Token": csrf},
    )
    assert changed.status_code == 204
    assert app_client.client.get("/api/auth/session").status_code == 200

    app_client.client.cookies.clear()
    old_login = app_client.client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "long-enough-password"},
        headers={"Origin": app_client.origin},
    )
    new_login = app_client.client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "new-long-enough-password"},
        headers={"Origin": app_client.origin},
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 204
