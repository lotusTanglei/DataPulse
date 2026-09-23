from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from datapulse.ai.models import AiAnalysisError, AiGatewayError, AiHealth
from datapulse.contracts.ai import (
    AiAnalysisResponse,
    AiChartResponse,
    AiScreenEditResponse,
    AiScreenResponse,
)
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
            "preview": {
                "request_id": "analysis-preview-1",
                "columns": (
                    {"name": "month", "data_type": "string"},
                    {"name": "amount", "data_type": "number"},
                ),
                "rows": (("2026-01", 100),),
                "row_count": 1,
                "truncated": False,
                "duration_ms": 2,
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


def screen_edit_response() -> AiScreenEditResponse:
    return AiScreenEditResponse.model_validate(
        {
            "plan": {
                "title": "销售运营大屏",
                "audience": "销售负责人",
                "narrative": "展示销售趋势。",
                "dataset_ids": ("sales",),
                "regions": ({"id": "main", "kind": "main"},),
                "widgets": (
                    {
                        "id": "trend",
                        "title": "销售趋势",
                        "intent": "展示月度销售趋势",
                        "region_id": "main",
                        "dataset_id": "sales",
                        "chart_type": "bar",
                        "dimensions": ("month",),
                        "measures": ({"field": "amount", "aggregation": "sum"},),
                    },
                ),
            },
            "document": {
                "canvas": {"width": 1920, "height": 1080},
                "components": (
                    {
                        "id": "trend",
                        "type": "builtin.bar",
                        "frame": {"x": 48, "y": 112, "width": 1824, "height": 900},
                    },
                ),
            },
            "affected_region_ids": ("main",),
            "report": {
                "valid": True,
                "widget_count": 1,
                "executed_count": 1,
                "fallback_count": 0,
            },
            "explanation": "已将趋势图改为柱状图。",
            "warnings": (),
        }
    )


@dataclass
class FakeAiService:
    status: AiHealth = AiHealth(status="unconfigured", model=None)
    response: AiAnalysisResponse = field(default_factory=ai_response)
    chart_response: AiChartResponse = field(default_factory=chart_response)
    screen_response: AiScreenResponse = field(default_factory=screen_response)
    screen_edit_response: AiScreenEditResponse = field(default_factory=screen_edit_response)
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

    async def edit_screen(self, payload, *, request_id: str):  # noqa: ANN001
        del payload, request_id
        if self.error is not None:
            raise self.error
        return self.screen_edit_response


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


def test_ai_screen_errors_expose_actionable_component_and_field_details(
    ai_app: AppClient,
) -> None:
    setup_admin(ai_app)
    ai_app.client.app.state.ai_service = FakeAiService(
        error=AiAnalysisError(
            "AI_FIELD_UNKNOWN",
            "The screen draft contains an unknown field.",
            issues=(
                {
                    "component_id": "sales-chart",
                    "field": "data_binding.chart_spec.dimensions[0]",
                    "reason": "字段不存在于数据集",
                    "expected": "已声明的数据集字段",
                },
            ),
        )
    )

    response = ai_app.client.post(
        "/api/admin/ai/screen",
        json={"question": "生成大屏", "dataset_ids": ["sales"]},
        headers=mutation_headers(ai_app),
    )

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "AI_FIELD_UNKNOWN",
        "message": "AI 使用了未知字段，请检查组件和字段绑定。",
        "request_id": response.headers["x-request-id"],
        "field_errors": [
            {
                "component_id": "sales-chart",
                "field": "data_binding.chart_spec.dimensions[0]",
                "reason": "字段不存在于数据集",
                "expected": "已声明的数据集字段",
            }
        ],
    }


def test_ai_rate_limit_error_keeps_429_status(ai_app: AppClient) -> None:
    setup_admin(ai_app)
    ai_app.client.app.state.ai_service = FakeAiService(
        error=AiGatewayError("AI_RATE_LIMITED", "provider rate limit")
    )

    response = ai_app.client.post(
        "/api/admin/ai/analyze",
        json={"question": "分析趋势", "dataset_ids": ["sales"]},
        headers=mutation_headers(ai_app),
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "AI_RATE_LIMITED"


def test_ai_screen_edit_api_returns_an_editable_draft_without_publishing(
    ai_app: AppClient,
) -> None:
    setup_admin(ai_app)
    response_payload = screen_edit_response()
    ai_app.client.app.state.ai_service = FakeAiService(
        screen_edit_response=response_payload
    )

    response = ai_app.client.post(
        "/api/admin/ai/screen/edit",
        json={
            "question": "把趋势图改成柱状图",
            "plan": response_payload.plan.model_dump(mode="json"),
            "document": response_payload.document.model_dump(mode="json"),
            "affected_region_ids": ["main"],
        },
        headers=mutation_headers(ai_app),
    )

    assert response.status_code == 200
    payload = AiScreenEditResponse.model_validate(response.json())
    assert payload.affected_region_ids == ("main",)
    assert payload.document.components[0].type == "builtin.bar"
    assert "published_document" not in response.json()


def test_ai_screen_edit_api_exposes_scope_errors(ai_app: AppClient) -> None:
    setup_admin(ai_app)
    response_payload = screen_edit_response()
    ai_app.client.app.state.ai_service = FakeAiService(
        error=AiAnalysisError(
            "AI_SCREEN_EDIT_INVALID",
            "The screen edit is invalid.",
            issues=(
                {
                    "component_id": "plan",
                    "field": "affected_region_ids",
                    "reason": "修改超出所选分区",
                    "expected": "只修改所选分区",
                },
            ),
        )
    )

    response = ai_app.client.post(
        "/api/admin/ai/screen/edit",
        json={
            "question": "修改主分区",
            "plan": response_payload.plan.model_dump(mode="json"),
            "document": response_payload.document.model_dump(mode="json"),
            "affected_region_ids": ["main"],
        },
        headers=mutation_headers(ai_app),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "AI_SCREEN_EDIT_INVALID"
    assert response.json()["error"]["field_errors"][0]["field"] == "affected_region_ids"
