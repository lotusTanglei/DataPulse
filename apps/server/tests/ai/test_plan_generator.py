from dataclasses import dataclass, field

import pytest

from datapulse.ai.models import DatasetContext
from datapulse.ai.plan_generator import ScreenPlanGenerator
from datapulse.contracts.ai import AiScreenRequest
from datapulse.contracts.dataset import DatasetDefinition
from datapulse.dataset.models import DatasetResponse

pytestmark = pytest.mark.anyio


def dataset() -> DatasetResponse:
    return DatasetResponse(
        id="sales",
        name="销售数据",
        data_source_id="source-1",
        definition=DatasetDefinition.model_validate(
            {
                "id": "sales",
                "name": "销售数据",
                "data_source_id": "source-1",
                "query": {"kind": "sql", "sql": "SELECT month, amount FROM sales"},
                "fields": (
                    {"name": "month", "data_type": "date"},
                    {"name": "amount", "data_type": "number"},
                ),
            }
        ),
        created_at="2026-09-23T00:00:00Z",
        updated_at="2026-09-23T00:00:00Z",
    )


def response_payload(*, dimension: str = "month") -> dict[str, object]:
    return {
        "plan": {
            "title": "销售总览",
            "audience": "销售负责人",
            "narrative": "先看趋势，再看关键指标。",
            "dataset_ids": ("sales",),
            "layout": {"template": "trend-focus", "grid_columns": 24},
            "regions": ({"id": "main", "kind": "main"},),
            "widgets": (
                {
                    "id": "trend",
                    "title": "销售趋势",
                    "intent": "展示月度销售额趋势",
                    "region_id": "main",
                    "dataset_id": "sales",
                    "chart_type": "line",
                    "dimensions": (dimension,),
                    "measures": ({"field": "amount", "aggregation": "sum"},),
                },
            ),
        },
        "explanation": "采用趋势聚焦骨架。",
        "warnings": (),
    }


@dataclass
class FakeGateway:
    payloads: list[dict[str, object]]
    calls: list[dict[str, object]] = field(default_factory=list)

    async def complete_json(self, *, system: str, user: str, response_model, **kwargs):  # noqa: ANN001
        del kwargs
        self.calls.append({"system": system, "user": user, "response_model": response_model})
        return response_model.model_validate(self.payloads.pop(0))


@dataclass
class FakeContextService:
    async def build(self, dataset_ids, *, max_rows: int, question: str | None = None):  # noqa: ANN001
        del max_rows, question
        return tuple(
            DatasetContext(
                dataset_id=dataset_id,
                name="销售数据",
                fields=(
                    {"name": "month", "data_type": "date", "role": "temporal"},
                    {"name": "amount", "data_type": "number", "role": "measure"},
                ),
                sample_rows=({"month": "2026-01-01", "amount": 120},),
                summary="2 fields; 1 sample row",
            )
            for dataset_id in dataset_ids
        )


@dataclass
class FakeDatasetRepository:
    async def get(self, dataset_id: str) -> DatasetResponse:
        assert dataset_id == "sales"
        return dataset()


async def test_ai_generates_validated_plan_without_pixel_coordinates() -> None:
    gateway = FakeGateway([response_payload()])
    generator = ScreenPlanGenerator(
        gateway=gateway,
        context_service=FakeContextService(),
        dataset_repository=FakeDatasetRepository(),
    )

    response = await generator.generate(
        AiScreenRequest(question="生成销售趋势大屏", dataset_ids=("sales",)),
        request_id="plan-1",
    )

    assert response.plan.widgets[0].dataset_id == "sales"
    assert response.plan.widgets[0].chart_type == "line"
    prompt = str(gateway.calls[0]["user"])
    assert "pixel coordinates" in prompt
    assert "single dataset_id" in prompt
    assert "cross-dataset join" in prompt


async def test_ai_plan_repairs_structured_validation_issues_for_at_most_two_rounds() -> None:
    gateway = FakeGateway(
        [response_payload(dimension="missing"), response_payload(dimension="month")]
    )
    generator = ScreenPlanGenerator(
        gateway=gateway,
        context_service=FakeContextService(),
        dataset_repository=FakeDatasetRepository(),
    )

    response = await generator.generate(
        AiScreenRequest(question="生成销售趋势大屏", dataset_ids=("sales",)),
        request_id="plan-repair",
    )

    assert response.plan.widgets[0].dimensions == ("month",)
    assert len(gateway.calls) == 2
    assert "PLAN_FIELD_UNKNOWN" in str(gateway.calls[1]["user"])
    assert "Repair the plan" in str(gateway.calls[1]["user"])
