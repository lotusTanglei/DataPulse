from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.support.app import AppClient, build_test_app

from datapulse.contracts.dashboard_plan import DashboardPlan
from datapulse.screen.models import (
    DashboardPlanCompileResponse,
    DashboardPlanRecompileResponse,
)
from datapulse.screen.planning_service import DashboardPlanningService
from tests.screen.test_planning_service import FakeRepository, plan


@pytest.fixture
def screen_app(tmp_path: Path) -> Iterator[AppClient]:
    with build_test_app(tmp_path) as app_client:
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


def test_screen_crud_requires_admin_and_csrf(screen_app: AppClient) -> None:
    assert screen_app.client.get("/api/admin/screens").status_code == 401
    setup_admin(screen_app)

    no_csrf = screen_app.client.post(
        "/api/admin/screens",
        json={"name": "Operations"},
        headers={"Origin": screen_app.origin},
    )
    assert no_csrf.status_code == 403

    created_response = screen_app.client.post(
        "/api/admin/screens",
        json={"name": "Operations", "description": "Live operations"},
        headers=mutation_headers(screen_app),
    )
    assert created_response.status_code == 201
    created = created_response.json()
    screen_id = created["id"]
    assert created["draft_revision"] == 0
    assert created["draft_document"]["canvas"] == {
        "width": 1920,
        "height": 1080,
        "background": {},
    }
    assert created["published_document"] is None
    assert screen_app.client.get("/api/admin/screens").json()[0]["id"] == screen_id
    assert screen_app.client.get(f"/api/admin/screens/{screen_id}").json() == created

    duplicate = screen_app.client.post(
        "/api/admin/screens",
        json={"name": "Operations"},
        headers=mutation_headers(screen_app),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "SCREEN_NAME_CONFLICT"

    renamed = screen_app.client.patch(
        f"/api/admin/screens/{screen_id}",
        json={"name": "Operations center"},
        headers=mutation_headers(screen_app),
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Operations center"

    copied = screen_app.client.post(
        f"/api/admin/screens/{screen_id}/copy",
        headers=mutation_headers(screen_app),
    )
    assert copied.status_code == 201
    assert copied.json()["name"] == "Operations center 副本"

    deleted = screen_app.client.delete(
        f"/api/admin/screens/{screen_id}",
        headers=mutation_headers(screen_app),
    )
    assert deleted.status_code == 204
    missing = screen_app.client.get(f"/api/admin/screens/{screen_id}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "SCREEN_NOT_FOUND"


def test_screen_draft_save_rejects_stale_revision(screen_app: AppClient) -> None:
    setup_admin(screen_app)
    created = screen_app.client.post(
        "/api/admin/screens",
        json={"name": "Operations"},
        headers=mutation_headers(screen_app),
    ).json()
    payload = {
        "expected_revision": 0,
        "draft_document": {
            "canvas": {"width": 1920, "height": 1080},
            "components": [],
        },
    }

    saved = screen_app.client.patch(
        f"/api/admin/screens/{created['id']}",
        json=payload,
        headers=mutation_headers(screen_app),
    )
    assert saved.status_code == 200
    assert saved.json()["draft_revision"] == 1

    stale = screen_app.client.patch(
        f"/api/admin/screens/{created['id']}",
        json=payload,
        headers=mutation_headers(screen_app),
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "SCREEN_REVISION_CONFLICT"


def test_screen_create_accepts_initial_document(screen_app: AppClient) -> None:
    setup_admin(screen_app)
    document = {
        "canvas": {"width": 1440, "height": 900},
        "components": [
            {
                "id": "text-1",
                "type": "builtin.text",
                "frame": {"x": 40, "y": 40, "width": 320, "height": 120},
            }
        ],
    }

    response = screen_app.client.post(
        "/api/admin/screens",
        json={"name": "Generated", "draft_document": document},
        headers=mutation_headers(screen_app),
    )

    assert response.status_code == 201
    created = response.json()
    assert created["draft_revision"] == 0
    assert created["draft_document"]["canvas"]["width"] == 1440
    assert created["draft_document"]["components"][0]["id"] == "text-1"


def test_screen_plan_compile_api_returns_plan_and_deterministic_document(
    screen_app: AppClient,
) -> None:
    setup_admin(screen_app)
    screen_app.app.state.screen_planning_service = DashboardPlanningService(
        dataset_repository=FakeRepository(calls=[])
    )

    response = screen_app.client.post(
        "/api/admin/screens/plan/compile",
        json={"plan": plan().model_dump(mode="json"), "canvas_width": 1440, "canvas_height": 900},
        headers=mutation_headers(screen_app),
    )

    assert response.status_code == 200
    payload = DashboardPlanCompileResponse.model_validate(response.json())
    assert payload.plan == plan()
    assert payload.document.canvas.width == 1440
    assert "frame" not in payload.plan.model_dump(mode="json")


def test_screen_plan_recompile_api_uses_the_same_planning_service(
    screen_app: AppClient,
) -> None:
    setup_admin(screen_app)
    screen_app.app.state.screen_planning_service = DashboardPlanningService(
        dataset_repository=FakeRepository(calls=[])
    )
    previous_plan = plan()
    compiled = screen_app.client.post(
        "/api/admin/screens/plan/compile",
        json={"plan": previous_plan.model_dump(mode="json")},
        headers=mutation_headers(screen_app),
    ).json()
    next_payload = previous_plan.model_dump(mode="json")
    next_payload["widgets"][0]["title"] = "销售额（修订）"
    next_plan = DashboardPlan.model_validate(next_payload)

    response = screen_app.client.post(
        "/api/admin/screens/plan/recompile",
        json={
            "previous_plan": previous_plan.model_dump(mode="json"),
            "plan": next_plan.model_dump(mode="json"),
            "document": compiled["document"],
            "affected_region_ids": ["summary"],
        },
        headers=mutation_headers(screen_app),
    )

    assert response.status_code == 200
    payload = DashboardPlanRecompileResponse.model_validate(response.json())
    assert payload.plan == next_plan
    assert payload.affected_region_ids == ("summary",)
    assert payload.document.components[1].props["label"] == "销售额（修订）"


def test_screen_publish_requires_csrf_and_matching_revision(
    screen_app: AppClient,
) -> None:
    setup_admin(screen_app)
    created = screen_app.client.post(
        "/api/admin/screens",
        json={"name": "Operations"},
        headers=mutation_headers(screen_app),
    ).json()
    publish_path = f"/api/admin/screens/{created['id']}/publish"

    no_csrf = screen_app.client.post(
        publish_path,
        json={"expected_revision": 0},
        headers={"Origin": screen_app.origin},
    )
    assert no_csrf.status_code == 403

    published = screen_app.client.post(
        publish_path,
        json={"expected_revision": 0},
        headers=mutation_headers(screen_app),
    )
    assert published.status_code == 200
    assert published.json()["published_document"] == created["draft_document"]
    assert published.json()["published_at"] is not None

    stale = screen_app.client.post(
        publish_path,
        json={"expected_revision": 1},
        headers=mutation_headers(screen_app),
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "SCREEN_REVISION_CONFLICT"
