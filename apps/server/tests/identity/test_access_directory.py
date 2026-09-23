from tests.identity.test_api import create_user, headers, login, system  # noqa: F401


def test_effective_permissions_follow_role_ceiling_and_revocation(system):  # noqa: F811
    viewer = create_user(system, "viewer", "viewer")
    screen = system.client.post(
        "/api/admin/screens", json={"name": "Shared"}, headers=headers(system.client)
    ).json()
    endpoint = f"/api/admin/identity/access/screen/{screen['id']}"
    client = login(system, "viewer")
    assert client.get(endpoint).status_code == 404
    grant = {
        "resource_type": "screen",
        "resource_id": screen["id"],
        "user_id": viewer["id"],
        "permission": "publish",
    }
    assert (
        system.client.put(
            "/api/admin/permissions", json=grant, headers=headers(system.client)
        ).status_code
        == 200
    )
    assert client.get(endpoint).json() == {
        "read": True,
        "write": False,
        "publish": False,
        "manage": False,
    }
    assert system.client.get(endpoint).json() == {
        "read": True,
        "write": True,
        "publish": True,
        "manage": True,
    }
    system.client.delete(
        f"/api/admin/permissions/screen/{screen['id']}/{viewer['id']}",
        headers=headers(system.client),
    )
    assert client.get(endpoint).status_code == 404
