from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

from datapulse.ecosystem.api import router
from datapulse.ecosystem.service import EcosystemService
from datapulse.errors import install_error_handlers
from tests.ecosystem.test_service import archive

pytestmark = pytest.mark.anyio


class Sessions:
    async def authenticate(self, token):
        if token not in {"admin", "editor", "viewer"}:
            return None
        return SimpleNamespace(id=token, username=token, role=token)

    async def verify_csrf(self, token, *, cookie_token, header_token):
        return cookie_token == header_token == "csrf"


@pytest.fixture
def application(tmp_path):
    app = FastAPI()
    install_error_handlers(app)
    app.state.session_service = Sessions()
    app.state.identity_service = SimpleNamespace()
    app.state.ecosystem_service = EcosystemService(root=tmp_path)
    app.include_router(router)
    return app


def client_for(app, role=None, csrf=True):
    cookies = {"datapulse_session": role, "datapulse_csrf": "csrf"} if role else {}
    headers = {"Origin": "http://test", "X-CSRF-Token": "csrf"} if csrf else {}
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        cookies=cookies,
        headers=headers,
    )


async def test_only_admin_can_install_and_mutations_require_csrf(application):
    for role, status in [(None, 401), ("viewer", 403), ("editor", 403)]:
        async with client_for(application, role) as client:
            response = await client.post(
                "/api/admin/ecosystem/packages",
                files={"file": ("metrics.zip", archive(), "application/zip")},
            )
            assert response.status_code == status
    async with client_for(application, "admin", csrf=False) as client:
        response = await client.post(
            "/api/admin/ecosystem/packages",
            files={"file": ("metrics.zip", archive(), "application/zip")},
        )
        assert response.status_code == 403
    assert application.state.ecosystem_service.list() == ()


async def test_catalog_install_list_detail_and_protected_plugin_asset(application):
    async with client_for(application, "admin") as client:
        response = await client.post(
            "/api/admin/ecosystem/packages",
            files={"file": ("metrics.zip", archive(), "application/zip")},
        )
        assert response.status_code == 201
        package = response.json()
        assert package["kind"] == "plugin"
        assert package["manifest"]["entry"] == "index.mjs"
    async with client_for(application, "editor") as client:
        response = await client.get("/api/admin/ecosystem/packages")
        assert response.json() == [package]
        detail = await client.get("/api/admin/ecosystem/packages/plugin/org.example.metrics/1.0.0")
        assert detail.json() == package
        asset = await client.get(
            "/api/admin/ecosystem/packages/plugin/org.example.metrics/1.0.0/files/index.mjs"
        )
        assert asset.status_code == 200
        assert asset.headers["content-type"].startswith("text/javascript")
        assert asset.headers["x-content-type-options"] == "nosniff"
    async with client_for(application) as client:
        assert (
            await client.get(
                "/api/admin/ecosystem/packages/plugin/org.example.metrics/1.0.0/files/index.mjs"
            )
        ).status_code == 401


async def test_template_apply_checks_transitive_dataset_permissions(application, services):
    from datapulse.errors import DataPulseError
    from tests.ecosystem.test_service import template_archive, template_document

    ecosystem, screens, _ = services
    application.state.ecosystem_service = ecosystem
    document = template_document()
    document["components"][0]["data_binding"] = {"dataset_id": "template-dataset"}
    ecosystem.install(template_archive(document, datasets=["template-dataset"]))
    calls = []

    class Identity:
        def require_creator(self, user):
            pass

        async def check_references(self, user, payload, **kwargs):
            pass

        async def require_access(self, user, kind, identifier, permission):
            calls.append((kind, identifier, permission))

        async def check_stored_references(self, user, kind, identifier):
            raise DataPulseError("AUTH_FORBIDDEN", "Datasource access is required.", 403)

    application.state.identity_service = Identity()
    async with client_for(application, "editor") as client:
        response = await client.post(
            "/api/admin/ecosystem/packages/template/org.example.board/1.0.0/apply",
            json={"name": "Mapped", "dataset_mapping": {"template-dataset": "shared-dataset"}},
        )
    assert response.status_code == 403
    assert calls == [("dataset", "shared-dataset", "read")]
    assert await screens.list() == ()


@pytest.mark.parametrize("guard_name", ["require_editor", "require_package_admin"])
async def test_missing_role_never_grants_ecosystem_privileges(guard_name):
    from datapulse.ecosystem import api
    from datapulse.errors import DataPulseError

    with pytest.raises(DataPulseError) as caught:
        await getattr(api, guard_name)(SimpleNamespace(id="legacy-user"))
    assert caught.value.status_code == 403


async def test_template_apply_requires_identity_even_for_an_admin(services):
    from datapulse.ecosystem.api import apply_template
    from datapulse.ecosystem.models import TemplateApply
    from datapulse.errors import DataPulseError
    from tests.ecosystem.test_service import template_archive

    ecosystem, screens, _ = services
    ecosystem.install(template_archive())
    request = SimpleNamespace(
        state=SimpleNamespace(admin=SimpleNamespace(id="admin", role="admin")),
        app=SimpleNamespace(state=SimpleNamespace(ecosystem_service=ecosystem)),
    )
    with pytest.raises(DataPulseError) as caught:
        await apply_template("org.example.board", "1.0.0", TemplateApply(name="Denied"), request)
    assert caught.value.status_code == 503
    assert await screens.list() == ()
