from dataclasses import dataclass

import pytest

from datapulse.contracts.dashboard_plan import DashboardPlan
from datapulse.contracts.dataset import DatasetDefinition
from datapulse.dataset.models import DatasetResponse
from datapulse.query.models import QueryResult
from datapulse.screen.models import (
    DashboardPlanCompileRequest,
    DashboardPlanRecompileRequest,
)
from datapulse.screen.planning_service import DashboardPlanningService
from datapulse.screen.runtime import ScreenDocumentQueryRequest

pytestmark = pytest.mark.anyio


def plan() -> DashboardPlan:
    return DashboardPlan.model_validate(
        {
            "title": "销售总览",
            "audience": "销售负责人",
            "narrative": "展示销售额。",
            "dataset_ids": ("sales",),
            "regions": ({"id": "summary", "kind": "summary"},),
            "widgets": (
                {
                    "id": "total",
                    "title": "销售额",
                    "intent": "展示销售额",
                    "region_id": "summary",
                    "dataset_id": "sales",
                    "chart_type": "kpi",
                    "measures": ({"field": "amount", "aggregation": "sum"},),
                },
            ),
        }
    )


def dataset() -> DatasetResponse:
    definition = DatasetDefinition.model_validate(
        {
            "id": "sales",
            "name": "销售数据",
            "query": {"kind": "sql", "sql": "SELECT amount FROM sales"},
            "fields": ({"name": "amount", "data_type": "number"},),
        }
    )
    return DatasetResponse(
        id="sales",
        name="销售数据",
        data_source_id=None,
        definition=definition,
        created_at="2026-09-23T00:00:00Z",
        updated_at="2026-09-23T00:00:00Z",
    )


@dataclass
class FakeRepository:
    calls: list[str]

    async def get(self, dataset_id: str) -> DatasetResponse:
        self.calls.append(dataset_id)
        return dataset()


@dataclass
class FakeRuntimeService:
    row_count: int
    calls: list[ScreenDocumentQueryRequest]

    async def query_document_component(
        self,
        data: ScreenDocumentQueryRequest,
        *,
        request_id: str,
    ) -> QueryResult:
        self.calls.append(data)
        return QueryResult(
            request_id=request_id,
            columns=(),
            rows=() if self.row_count == 0 else ((42,),),
            row_count=self.row_count,
            truncated=False,
            duration_ms=1,
        )


async def test_manual_compile_uses_core_plan_validator_and_document_compiler() -> None:
    repository = FakeRepository(calls=[])
    service = DashboardPlanningService(dataset_repository=repository)

    response = await service.compile(
        DashboardPlanCompileRequest(plan=plan(), canvas_width=1440, canvas_height=900)
    )

    assert repository.calls == ["sales"]
    assert response.plan == plan()
    assert response.document.canvas.width == 1440
    assert response.document.components[1].data_binding["chart_spec"]["dataset_id"] == "sales"
    assert "frame" not in response.plan.model_dump(mode="json")


async def test_manual_compile_preflights_charts_and_returns_self_check_report() -> None:
    runtime = FakeRuntimeService(row_count=0, calls=[])
    service = DashboardPlanningService(
        dataset_repository=FakeRepository(calls=[]),
        runtime_service=runtime,
    )

    response = await service.compile(
        DashboardPlanCompileRequest(plan=plan()),
        request_id="plan-preflight",
    )

    assert [call.component_id for call in runtime.calls] == ["total"]
    assert response.report is not None
    assert response.report.executed_count == 1
    assert response.report.fallback_count == 1
    assert response.document.components[1].type == "builtin.panel"
    assert response.warnings == (
        "组件 total 已降级为占位：图表查询结果为空",
    )


async def test_manual_recompile_uses_same_core_planning_service() -> None:
    repository = FakeRepository(calls=[])
    service = DashboardPlanningService(dataset_repository=repository)
    previous_plan = plan()
    compiled = await service.compile(DashboardPlanCompileRequest(plan=previous_plan))
    next_payload = previous_plan.model_dump(mode="json")
    next_payload["widgets"][0]["title"] = "销售额（修订）"
    next_plan = DashboardPlan.model_validate(next_payload)

    response = await service.recompile(
        DashboardPlanRecompileRequest(
            previous_plan=previous_plan,
            plan=next_plan,
            document=compiled.document,
            affected_region_ids=("summary",),
        )
    )

    assert repository.calls == ["sales", "sales"]
    assert response.plan == next_plan
    assert response.affected_region_ids == ("summary",)
    assert response.document.components[1].props["label"] == "销售额（修订）"
