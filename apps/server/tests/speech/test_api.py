from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from datapulse.contracts.speech import DigitalHumanPlaybackDiagnosticResponse
from datapulse.speech.service import SpeechProviderUnavailable
from tests.support.app import AppClient, build_test_app


@pytest.fixture
def speech_app(tmp_path: Path) -> Iterator[AppClient]:
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


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("?screen_id=screen-a&component_id=speaker-a&limit=1", 1),
        ("?screen_id=screen-a", 2),
    ],
)
def test_playback_diagnostics_http_filters_and_redacts_payload(
    speech_app: AppClient,
    monkeypatch: pytest.MonkeyPatch,
    query: str,
    expected: int,
) -> None:
    setup_admin(speech_app)
    diagnostics = (
        DigitalHumanPlaybackDiagnosticResponse(
            screen_id="screen-a",
            component_id="speaker-a",
            task_id="task-1",
            status="failed",
            provider_id="provider-1",
            source="runtime",
            asset_id="",
            error_code="SPEECH_PROVIDER_UNAVAILABLE",
            created_at=datetime(2026, 1, 2, tzinfo=UTC),
        ),
        DigitalHumanPlaybackDiagnosticResponse(
            screen_id="screen-a",
            component_id="speaker-b",
            task_id="task-2",
            status="succeeded",
            provider_id="provider-1",
            source="manual",
            asset_id="asset-2",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
    )

    async def fake_diagnostics(
        **filters: object,
    ) -> tuple[DigitalHumanPlaybackDiagnosticResponse, ...]:
        selected = diagnostics
        if filters.get("screen_id"):
            selected = tuple(item for item in selected if item.screen_id == filters["screen_id"])
        if filters.get("component_id"):
            selected = tuple(
                item for item in selected if item.component_id == filters["component_id"]
            )
        return selected[: int(filters["limit"])]

    monkeypatch.setattr(
        speech_app.app.state.speech_service,
        "playback_diagnostics",
        fake_diagnostics,
    )
    response = speech_app.client.get(f"/api/admin/digital-human/diagnostics{query}")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == expected
    assert all("text" not in item and "query_result" not in item for item in body)


def test_playback_diagnostics_http_rejects_invalid_limit(speech_app: AppClient) -> None:
    setup_admin(speech_app)

    response = speech_app.client.get("/api/admin/digital-human/diagnostics?limit=0")

    assert response.status_code == 422


def test_speech_plan_preview_returns_stable_governance_error(
    speech_app: AppClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_admin(speech_app)

    async def rejected_plan(_payload: object) -> object:
        raise SpeechProviderUnavailable("SPEECH_CONTENT_FORBIDDEN_WORD")

    monkeypatch.setattr(speech_app.app.state.speech_service, "create_plan", rejected_plan)
    response = speech_app.client.post(
        "/api/admin/digital-human/plans/preview",
        headers={
            "Origin": speech_app.origin,
            "X-CSRF-Token": speech_app.client.cookies["datapulse_csrf"],
        },
        json={
            "screen_id": "screen-1",
            "component_id": "speaker-1",
            "text": "被禁播内容",
            "language": "zh-CN",
            "provider_id": "provider-1",
            "voice": "alloy",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SPEECH_CONTENT_FORBIDDEN_WORD"


def test_metrics_prometheus_http_exports_low_cardinality_snapshot(
    speech_app: AppClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_admin(speech_app)

    async def fake_metrics() -> object:
        return type(
            "Metrics",
            (),
            {
                "tasks_queued": 2,
                "tasks_succeeded": 3,
                "tasks_failed": 1,
                "tasks_cancelled": 4,
                "cache_hits": 5,
                "synthesis_attempts": 6,
                "synthesis_failures": 1,
                "synthesis_total_ms": 120.5,
                "average_synthesis_ms": 20.08,
            },
        )()

    monkeypatch.setattr(speech_app.app.state.speech_service, "metrics_snapshot", fake_metrics)
    response = speech_app.client.get("/api/admin/digital-human/metrics/prometheus")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert 'service="datapulse",feature="digital_human"' in response.text
    assert "datapulse_digital_human_speech_tasks_succeeded_total" in response.text
    assert "screen_id" not in response.text
    assert response.text.endswith("\n")


def test_internal_metrics_requires_configured_bearer_token(
    speech_app: AppClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    endpoint = "/api/internal/digital-human/metrics/prometheus"
    assert speech_app.client.get(endpoint).status_code == 401
    speech_app.app.state.settings.metrics_token = "metrics-test-token"

    async def fake_metrics() -> object:
        return type(
            "Metrics",
            (),
            {
                "tasks_queued": 1,
                "tasks_succeeded": 1,
                "tasks_failed": 0,
                "tasks_cancelled": 0,
                "cache_hits": 0,
                "synthesis_attempts": 1,
                "synthesis_failures": 0,
                "synthesis_total_ms": 12,
                "average_synthesis_ms": 12,
            },
        )()

    monkeypatch.setattr(speech_app.app.state.speech_service, "metrics_snapshot", fake_metrics)
    assert speech_app.client.get(endpoint).status_code == 401
    assert speech_app.client.get(
        endpoint, headers={"Authorization": "Bearer wrong"}
    ).status_code == 401
    response = speech_app.client.get(
        endpoint,
        headers={"Authorization": "Bearer metrics-test-token"},
    )
    assert response.status_code == 200
    assert "# TYPE datapulse_digital_human_speech_tasks_succeeded_total counter" in response.text
    assert "# TYPE datapulse_digital_human_speech_average_synthesis_ms gauge" in response.text
