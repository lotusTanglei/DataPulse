from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from datapulse.ai.models import AiAnalysisError, AiHealth
from datapulse.contracts.ai import AiAnalysisResponse, AiChartResponse, AiScreenResponse
from tests.support.app import AppClient, build_test_app


@pytest.fixture
def ai_app(tmp_path: Path) -> Iterator[AppClient]:
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


def ai_response() -> AiAnalysisResponse:
    return AiAnalysisResponse.model_validate(
        {
            "plan": {
                "question": "按月份汇总销售额",
                "dataset_ids": ("sales",),
                "dimensions": ("month",),
                "measures": ({"field": "amount", "aggregation": "sum"},),
                "filters": (),
                "sort": (),
                "recommended_chart": "line",
                "assumptions": (),
                "requires_confirmation": True,
            },
            "narrative": "销售额整体上升。",
            "chart_spec": {
                "dataset_id": "sales",
                "dimensions": ("month",),
                "measures": ({"field": "amount", "aggregation": "sum"},),
                "visual": {"type": "line"},
            },
            "warnings": (),
        }
    )


def chart_response() -> AiChartResponse:
    return AiChartResponse.model_validate(
        {
            "chart_spec": {
                "dataset_id": "sales",
                "dimensions": ("region",),
                "measures": ({"field": "amount", "aggregation": "sum"},),
                "visual": {"type": "bar"},
            },
            "explanation": "按区域统计销售额。",
            "preview": {
                "request_id": "preview-1",
                "columns": (
                    {"name": "region", "data_type": "string"},
                    {"name": "amount", "data_type": "number"},
                ),
                "rows": (("north", 10),),
                "row_count": 1,
                "truncated": False,
                "duration_ms": 2,
            },
            "warnings": (),
        }
    )


def screen_response() -> AiScreenResponse:
    return AiScreenResponse.model_validate(
        {
            "document": {
                "canvas": {"width": 1920, "height": 1080},
                "theme": {"id": "datapulse-dark", "tokens": {}},
                "refresh": {"mode": "disabled"},
                "parameters": (),
                "components": (
                    {
                        "id": "title",
                        "type": "builtin.text",
                        "frame": {"x": 40, "y": 24, "width": 720, "height": 80},
                        "props": {"text": "销售运营大屏"},
                    },
                ),
            },
            "explanation": "生成销售运营概览。",
            "warnings": (),
        }
    )


@dataclass
class FakeAiService:
    status: AiHealth = AiHealth(status="unconfigured", model=None)
    response: AiAnalysisResponse = field(default_factory=ai_response)
    chart_response: AiChartResponse = field(default_factory=chart_response)
    screen_response: AiScreenResponse = field(default_factory=screen_response)
    error: Exception | None = None

    def health(self) -> AiHealth:
        return self.status

    async def analyze(self, payload, *, request_id: str):  # noqa: ANN001
        del payload, request_id
        if self.error is not None:
            raise self.error
        return self.response

    async def generate_chart(self, payload, *, request_id: str):  # noqa: ANN001
        del payload, request_id
        if self.error is not None:
            raise self.error
        return self.chart_response

    async def generate_screen(self, payload, *, request_id: str):  # noqa: ANN001
        del payload, request_id
        if self.error is not None:
            raise self.error
        return self.screen_response


def test_ai_status_and_analyze_require_admin_and_map_errors(ai_app: AppClient) -> None:
    assert ai_app.client.get("/api/admin/ai/status").status_code == 401
    setup_admin(ai_app)

    ai_app.client.app.state.ai_service = FakeAiService(
        status=AiHealth(status="configured", model="gpt-4.1-mini")
    )
    status = ai_app.client.get("/api/admin/ai/status")
    assert status.status_code == 200
    assert status.json() == {"status": "configured", "model": "gpt-4.1-mini"}

    no_csrf = ai_app.client.post(
        "/api/admin/ai/analyze",
        json={"question": "分析趋势", "dataset_ids": ["sales"], "mode": "analysis"},
        headers={"Origin": ai_app.origin},
    )
    assert no_csrf.status_code == 403

    ai_app.client.app.state.ai_service = FakeAiService(
        error=AiAnalysisError("AI_DATASET_INVALID", "The dataset is invalid.")
    )
    invalid = ai_app.client.post(
        "/api/admin/ai/analyze",
        json={"question": "分析趋势", "dataset_ids": ["sales"], "mode": "analysis"},
        headers=mutation_headers(ai_app),
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "AI_DATASET_INVALID"

    chart = ai_app.client.post(
        "/api/admin/ai/chart",
        json={
            "question": "按区域统计销售额",
            "dataset_id": "sales",
            "target_component_type": "bar",
        },
        headers=mutation_headers(ai_app),
    )
    assert chart.status_code == 422
    assert chart.json()["error"]["code"] == "AI_DATASET_INVALID"

    ai_app.client.app.state.ai_service = FakeAiService()
    chart_success = ai_app.client.post(
        "/api/admin/ai/chart",
        json={
            "question": "按区域统计销售额",
            "dataset_id": "sales",
            "target_component_type": "bar",
        },
        headers=mutation_headers(ai_app),
    )
    assert chart_success.status_code == 200
    assert chart_success.json()["chart_spec"]["visual"]["type"] == "bar"
    assert chart_success.json()["preview"]["rows"] == [["north", 10]]

    screen_success = ai_app.client.post(
        "/api/admin/ai/screen",
        json={
            "question": "生成销售运营大屏",
            "dataset_ids": ["sales"],
            "canvas_width": 1920,
            "canvas_height": 1080,
            "theme": "dark",
        },
        headers=mutation_headers(ai_app),
    )
    assert screen_success.status_code == 200
    assert screen_success.json()["document"]["components"][0]["type"] == "builtin.text"
