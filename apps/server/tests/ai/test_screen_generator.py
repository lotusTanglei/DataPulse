from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from datapulse.ai.models import AiAnalysisError, AiHealth, DatasetContext
from datapulse.ai.screen_generator import ScreenDraftGenerator, validate_ai_document
from datapulse.contracts.ai import AiScreenRequest
from datapulse.contracts.dataset import (
    CachePolicy,
    DataType,
    DatasetDefinition,
    DatasetField,
    DatasetParameter,
    RefreshPolicy,
    SqlQuery,
)
from datapulse.dataset.models import DatasetResponse
from datapulse.dataset.repository import DatasetNotFound

pytestmark = pytest.mark.anyio


def sales_dataset_response() -> DatasetResponse:
    return DatasetResponse(
        id="sales",
        name="销售数据集",
        data_source_id="source-1",
        definition=DatasetDefinition(
            id="sales",
            name="销售数据集",
            data_source_id="source-1",
            query=SqlQuery(sql="SELECT month, region, order_id, amount, progress FROM sales"),
            fields=(
                DatasetField(name="month", data_type=DataType.STRING),
                DatasetField(name="region", data_type=DataType.STRING),
                DatasetField(name="order_id", data_type=DataType.STRING),
                DatasetField(name="amount", data_type=DataType.NUMBER),
                DatasetField(name="progress", data_type=DataType.NUMBER),
            ),
            parameters=(
                DatasetParameter(
                    name="region",
                    data_type=DataType.STRING,
                    required=False,
                    default="east",
                ),
            ),
            cache=CachePolicy(),
            refresh=RefreshPolicy(),
            max_rows=5000,
            timeout_seconds=30,
        ),
        created_at="2026-08-01T00:00:00Z",
        updated_at="2026-08-01T00:00:00Z",
    )


def contexts() -> tuple[DatasetContext, ...]:
    return (
        DatasetContext(
            dataset_id="sales",
            name="销售数据集",
            fields=(
                {"name": "month", "data_type": "string"},
                {"name": "region", "data_type": "string"},
                {"name": "order_id", "data_type": "string"},
                {"name": "amount", "data_type": "number"},
                {"name": "progress", "data_type": "number"},
            ),
            sample_rows=(
                {
                    "month": "2026-01",
                    "region": "east",
                    "order_id": "SO-1",
                    "amount": 120,
                    "progress": 86,
                },
            ),
            summary="5 fields; 1 sample rows; 1 parameters.",
        ),
    )


def screen_payload() -> dict[str, object]:
    return {
        "document": {
            "components": [
                {
                    "type": "builtin.text",
                    "frame": {"x": 40, "y": 24, "width": 720, "height": 80},
                    "props": {"text": "销售运营大屏", "align": "left", "font_size": 32},
                },
                {
                    "type": "builtin.kpi",
                    "frame": {"x": 40, "y": 128, "width": 260, "height": 140},
                    "props": {"label": "销售额"},
                    "data_binding": {
                        "chart_spec": {
                            "dataset_id": "sales",
                            "dimensions": [],
                            "measures": [{"field": "amount", "aggregation": "sum"}],
                            "visual": {"type": "kpi", "title": "销售额"},
                        }
                    },
                },
                {
                    "type": "builtin.line",
                    "frame": {"x": 320, "y": 128, "width": 760, "height": 320},
                    "data_binding": {
                        "chart_spec": {
                            "dataset_id": "sales",
                            "dimensions": ["month"],
                            "measures": [{"field": "amount", "aggregation": "sum"}],
                            "filters": [
                                {
                                    "field": "region",
                                    "operator": "equals",
                                    "value": {"kind": "parameter", "name": "region"},
                                }
                            ],
                            "sort": [{"field": "month", "direction": "asc"}],
                            "visual": {"type": "line", "title": "月度销售趋势"},
                        }
                    },
                },
                {
                    "type": "builtin.bar",
                    "frame": {"x": 1100, "y": 128, "width": 640, "height": 320},
                    "data_binding": {
                        "chart_spec": {
                            "dataset_id": "sales",
                            "dimensions": ["region"],
                            "measures": [{"field": "amount", "aggregation": "sum"}],
                            "sort": [{"field": "amount", "direction": "desc"}],
                            "visual": {"type": "bar", "title": "区域销售排名"},
                        }
                    },
                },
                {
                    "type": "builtin.table",
                    "frame": {"x": 40, "y": 472, "width": 1700, "height": 420},
                    "props": {"max_rows": 20},
                    "data_binding": {
                        "chart_spec": {
                            "dataset_id": "sales",
                            "dimensions": ["month", "region", "order_id"],
                            "measures": [{"field": "amount", "aggregation": "sum"}],
                            "sort": [{"field": "month", "direction": "desc"}],
                            "visual": {"type": "table", "title": "订单明细"},
                        }
                    },
                },
            ],
            "parameters": [
                {
                    "id": "region-filter",
                    "name": "region",
                    "data_type": "string",
                    "default": "east",
                    "mutable": True,
                    "allowed_values": ["east", "west"],
                }
            ],
        },
        "explanation": "生成销售运营概览，包含总览指标、趋势、排行和明细。",
        "warnings": (),
    }


@dataclass
class FakeGateway:
    payload: dict[str, object]
    calls: list[dict[str, object]] = field(default_factory=list)
    status: AiHealth = AiHealth(status="configured", model="gpt-4.1-mini")

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        response_model,  # noqa: ANN001
    ):
        self.calls.append(
            {"system": system, "user": user, "response_model": response_model}
        )
        return response_model.model_validate(self.payload)

    def health(self) -> AiHealth:
        return self.status


@dataclass
class FakeContextService:
    contexts: tuple[DatasetContext, ...]
    calls: list[dict[str, object]] = field(default_factory=list)

    async def build(
        self,
        dataset_ids: tuple[str, ...],
        *,
        max_rows: int,
    ) -> tuple[DatasetContext, ...]:
        self.calls.append({"dataset_ids": dataset_ids, "max_rows": max_rows})
        return self.contexts


@dataclass
class FakeDatasetRepository:
    datasets: dict[str, DatasetResponse]

    async def get(self, dataset_id: str) -> DatasetResponse:
        if dataset_id not in self.datasets:
            raise DatasetNotFound(dataset_id)
        return self.datasets[dataset_id]


def build_generator(payload: dict[str, object]) -> tuple[ScreenDraftGenerator, FakeGateway]:
    gateway = FakeGateway(payload=payload)
    generator = ScreenDraftGenerator(
        gateway=gateway,
        context_service=FakeContextService(contexts=contexts()),
        dataset_repository=FakeDatasetRepository({"sales": sales_dataset_response()}),
        max_context_rows=100,
    )
    return generator, gateway


async def test_screen_generator_builds_validated_dashboard_document() -> None:
    generator, gateway = build_generator(screen_payload())

    response = await generator.generate(
        AiScreenRequest(
            question="生成销售运营大屏",
            dataset_ids=("sales",),
            theme="dark",
        ),
        request_id="screen-req-1",
    )

    assert response.document.canvas.width == 1920
    assert response.document.canvas.height == 1080
    assert response.document.theme.id == "datapulse-dark"
    assert response.document.refresh.mode == "disabled"
    assert len(response.document.parameters) == 1
    assert {component.type for component in response.document.components} >= {
        "builtin.text",
        "builtin.kpi",
        "builtin.line",
        "builtin.bar",
        "builtin.table",
    }
    assert all(component.id for component in response.document.components)
    assert "allowed_component_types:" in str(gateway.calls[0]["user"])


@pytest.mark.parametrize(
    ("mutator", "error_code"),
    [
        (
            lambda payload: payload["components"].__setitem__(
                0,
                {
                    "type": "plugin.unknown",
                    "frame": {"x": 40, "y": 24, "width": 720, "height": 80},
                },
            ),
            "AI_SCREEN_INVALID",
        ),
        (
            lambda payload: payload["components"][1]["data_binding"]["chart_spec"].__setitem__(
                "dataset_id",
                "other",
            ),
            "AI_DATASET_INVALID",
        ),
        (
            lambda payload: payload["components"][2]["data_binding"]["chart_spec"].__setitem__(
                "dimensions",
                ["missing"],
            ),
            "AI_SCREEN_INVALID",
        ),
        (
            lambda payload: payload["components"][3].__setitem__(
                "frame",
                {"x": 1600, "y": 128, "width": 640, "height": 320},
            ),
            "AI_SCREEN_INVALID",
        ),
        (
            lambda payload: payload["components"][0]["props"].__setitem__(
                "script",
                "alert('xss')",
            ),
            "AI_SCREEN_INVALID",
        ),
        (
            lambda payload: payload.__setitem__(
                "components",
                [
                    {
                        "id": f"text-{index}",
                        "type": "builtin.text",
                        "frame": {"x": 0, "y": index * 10, "width": 100, "height": 20},
                        "props": {"text": f"组件 {index}"},
                    }
                    for index in range(13)
                ],
            ),
            "AI_SCREEN_INVALID",
        ),
        (
            lambda payload: payload.__setitem__("auto_publish", True),
            "AI_SCREEN_INVALID",
        ),
    ],
)
def test_validate_ai_document_rejects_invalid_payloads(
    mutator,
    error_code: str,
) -> None:
    payload = screen_payload()["document"]
    mutator(payload)

    with pytest.raises(AiAnalysisError) as error:
        validate_ai_document(
            payload,
            allowed_dataset_ids={"sales": sales_dataset_response()},
            canvas_width=1920,
            canvas_height=1080,
            requested_theme="dark",
        )

    assert error.value.code == error_code
