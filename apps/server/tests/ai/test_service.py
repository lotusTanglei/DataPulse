from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import pytest

from datapulse.ai.models import AiAnalysisError, AiGatewayError, AiHealth, DatasetContext
from datapulse.ai.service import AiService
from datapulse.contracts.ai import (
    AiAnalysisDraft,
    AiAnalysisRequest,
    AiScreenEditRequest,
    AiScreenRequest,
)
from datapulse.contracts.chart import ChartSpec
from datapulse.contracts.dashboard_plan import DashboardPlan
from datapulse.contracts.dataset import (
    CachePolicy,
    DatasetDefinition,
    DatasetField,
    DatasetParameter,
    DataType,
    RefreshPolicy,
    SqlQuery,
)
from datapulse.dataset.models import DatasetResponse
from datapulse.dataset.repository import DatasetNotFound
from datapulse.filedata.repository import FileAssetNotFound
from datapulse.query.models import QueryColumn, QueryRequest, QueryResult
from datapulse.screen.models import (
    DashboardPlanCompileRequest,
    DashboardPlanRecompileRequest,
)
from datapulse.screen.planning_service import DashboardPlanningService
from datapulse.screen.runtime import ScreenDocumentQueryRequest

pytestmark = pytest.mark.anyio


def sql_dataset_response() -> DatasetResponse:
    return DatasetResponse(
        id="sales",
        name="销售数据集",
        data_source_id="source-1",
        definition=DatasetDefinition(
            id="sales",
            name="销售数据集",
            data_source_id="source-1",
            query=SqlQuery(sql="SELECT month, amount FROM sales"),
            fields=(
                DatasetField(name="month", data_type=DataType.STRING),
                DatasetField(name="region", data_type=DataType.STRING),
                DatasetField(name="amount", data_type=DataType.NUMBER),
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


def ai_response() -> AiAnalysisDraft:
    return AiAnalysisDraft.model_validate(
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
            "chart_spec": None,
            "warnings": (),
        }
    )


@dataclass
class FakeGateway:
    response: object
    calls: list[dict[str, object]] = field(default_factory=list)
    status: AiHealth = AiHealth(status="configured", model="gpt-4.1-mini")
    ensure_error: AiGatewayError | None = None
    ensure_calls: int = 0

    def ensure_configured(self) -> None:
        self.ensure_calls += 1
        if self.ensure_error is not None:
            raise self.ensure_error

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        response_model,
    ):
        self.calls.append(
            {
                "system": system,
                "user": user,
                "response_model": response_model,
            }
        )
        return response_model.model_validate(self.response)

    def health(self) -> AiHealth:
        return self.status


@dataclass
class FakeContextService:
    contexts: tuple[DatasetContext, ...]
    calls: list[dict[str, object]] = field(default_factory=list)
    error: Exception | None = None

    async def build(
        self,
        dataset_ids: tuple[str, ...],
        *,
        max_rows: int,
        question: str | None = None,
    ) -> tuple[DatasetContext, ...]:
        self.calls.append({"dataset_ids": dataset_ids, "max_rows": max_rows, "question": question})
        if self.error is not None:
            raise self.error
        return self.contexts


@dataclass
class FakeDatasetRepository:
    datasets: dict[str, DatasetResponse]

    async def get(self, dataset_id: str) -> DatasetResponse:
        if dataset_id not in self.datasets:
            raise DatasetNotFound(dataset_id)
        return self.datasets[dataset_id]


@dataclass
class RecordingPlanningService:
    inner: DashboardPlanningService
    compile_calls: list[DashboardPlanCompileRequest] = field(default_factory=list)
    recompile_calls: list[DashboardPlanRecompileRequest] = field(default_factory=list)
    compile_request_ids: list[str] = field(default_factory=list)
    recompile_request_ids: list[str] = field(default_factory=list)

    async def compile(
        self,
        request: DashboardPlanCompileRequest,
        *,
        request_id: str = "plan-compile",
    ):  # noqa: ANN201
        self.compile_calls.append(request)
        self.compile_request_ids.append(request_id)
        return await self.inner.compile(request, request_id=request_id)

    async def recompile(
        self,
        request: DashboardPlanRecompileRequest,
        *,
        request_id: str = "plan-recompile",
    ):  # noqa: ANN201
        self.recompile_calls.append(request)
        self.recompile_request_ids.append(request_id)
        return await self.inner.recompile(request, request_id=request_id)


@dataclass
class FakePlanningRuntime:
    calls: list[ScreenDocumentQueryRequest] = field(default_factory=list)
    row_counts: tuple[int, ...] = ()

    async def query_document_component(
        self,
        data: ScreenDocumentQueryRequest,
        *,
        request_id: str,
    ) -> QueryResult:
        self.calls.append(data)
        row_count = (
            self.row_counts[len(self.calls) - 1] if len(self.calls) <= len(self.row_counts) else 1
        )
        return QueryResult(
            request_id=request_id,
            columns=(QueryColumn(name="amount", data_type="number"),),
            rows=((100,),) if row_count else (),
            row_count=row_count,
            truncated=False,
            duration_ms=1,
        )


@dataclass
class FakeConnector:
    type: str = "sqlite"
    dialect: str = "sqlite"


@dataclass
class FakeSource:
    id: str = "source-1"
    config: object = field(default_factory=lambda: type("Config", (), {"type": "sqlite"})())


@dataclass
class FakeDatasourceService:
    calls: list[dict[str, object]] = field(default_factory=list)

    async def get(self, datasource_id: str) -> object:
        return FakeSource(id=datasource_id)

    async def query(
        self,
        datasource_id: str,
        request: QueryRequest,
        *,
        request_id: str,
        dataset_id: str | None = None,
        trigger: str = "debug",
    ) -> QueryResult:
        self.calls.append(
            {
                "datasource_id": datasource_id,
                "request": request,
                "request_id": request_id,
                "dataset_id": dataset_id,
                "trigger": trigger,
            }
        )
        return QueryResult(
            request_id=request_id,
            columns=(
                QueryColumn(name="month", data_type="string"),
                QueryColumn(name="amount", data_type="number"),
            ),
            rows=(("2026-01", 100),),
            row_count=1,
            truncated=False,
            duration_ms=3,
        )


def contexts() -> tuple[DatasetContext, ...]:
    return (
        DatasetContext(
            dataset_id="sales",
            name="销售数据集",
            fields=(
                {"name": "month", "data_type": "string"},
                {"name": "region", "data_type": "string"},
                {"name": "amount", "data_type": "number"},
            ),
            sample_rows=({"month": "2026-01", "region": "east", "amount": 100},),
            summary="3 fields; 1 sample rows; 1 parameters.",
        ),
    )


def screen_plan_response() -> dict[str, object]:
    return {
        "plan": {
            "title": "销售运营大屏",
            "audience": "销售负责人",
            "narrative": "先看销售额，再看月度趋势。",
            "dataset_ids": ("sales",),
            "regions": (
                {"id": "summary", "kind": "summary", "order": 0},
                {"id": "main", "kind": "main", "order": 1},
            ),
            "widgets": (
                {
                    "id": "sales-total",
                    "title": "销售额",
                    "intent": "展示销售额",
                    "region_id": "summary",
                    "dataset_id": "sales",
                    "chart_type": "kpi",
                    "measures": ({"field": "amount", "aggregation": "sum"},),
                },
                {
                    "id": "sales-trend",
                    "title": "销售趋势",
                    "intent": "展示月度销售趋势",
                    "region_id": "main",
                    "dataset_id": "sales",
                    "chart_type": "line",
                    "dimensions": ("month",),
                    "measures": ({"field": "amount", "aggregation": "sum"},),
                },
            ),
        },
        "explanation": "生成销售运营大屏草稿。",
        "warnings": (),
    }


async def test_service_builds_context_prompt_validates_chart_and_previews() -> None:
    gateway = FakeGateway(response=ai_response())
    context_service = FakeContextService(contexts=contexts())
    datasource_service = FakeDatasourceService()
    service = AiService(
        gateway=gateway,
        context_service=context_service,
        dataset_repository=FakeDatasetRepository({"sales": sql_dataset_response()}),
        datasource_service=datasource_service,
        registry=type("Registry", (), {"get": lambda self, _name: FakeConnector()})(),
        max_context_rows=100,
    )

    response = await service.analyze(
        AiAnalysisRequest(
            question="分析最近几个月的销售趋势",
            dataset_ids=("sales",),
            mode="chart",
        ),
        request_id="ai-req-1",
    )

    assert response.narrative == "销售额整体上升。"
    assert isinstance(response.chart_spec, ChartSpec)
    assert response.chart_spec.visual.type.value == "line"
    assert response.preview.rows == (("2026-01", 100),)
    assert context_service.calls == [
        {
            "dataset_ids": ("sales",),
            "max_rows": 100,
            "question": "分析最近几个月的销售趋势",
        }
    ]
    assert len(gateway.calls) == 1
    assert "contexts:" in str(gateway.calls[0]["user"])
    assert datasource_service.calls[0]["trigger"] == "ai-analyze"
    assert "FROM (SELECT month, amount FROM sales)" in datasource_service.calls[0]["request"].sql


async def test_service_rejects_unconfigured_before_reading_dataset_context() -> None:
    gateway = FakeGateway(
        response=ai_response(),
        ensure_error=AiGatewayError("AI_NOT_CONFIGURED", "AI is not configured."),
    )
    context_service = FakeContextService(contexts=contexts())
    datasource_service = FakeDatasourceService()
    service = AiService(
        gateway=gateway,
        context_service=context_service,
        dataset_repository=FakeDatasetRepository({"sales": sql_dataset_response()}),
        datasource_service=datasource_service,
        registry=type("Registry", (), {"get": lambda self, _name: FakeConnector()})(),
    )

    with pytest.raises(AiGatewayError) as error:
        await service.analyze(
            AiAnalysisRequest(question="分析销售趋势", dataset_ids=("sales",)),
            request_id="ai-unconfigured",
        )

    assert error.value.code == "AI_NOT_CONFIGURED"
    assert gateway.ensure_calls == 1
    assert context_service.calls == []
    assert datasource_service.calls == []


async def test_service_rejects_missing_dataset_before_context_and_model() -> None:
    gateway = FakeGateway(response=ai_response())
    context_service = FakeContextService(contexts=contexts())
    service = AiService(
        gateway=gateway,
        context_service=context_service,
        dataset_repository=FakeDatasetRepository({}),
        datasource_service=FakeDatasourceService(),
        registry=type("Registry", (), {"get": lambda self, _name: FakeConnector()})(),
    )

    with pytest.raises(AiAnalysisError) as error:
        await service.analyze(
            AiAnalysisRequest(question="分析销售趋势", dataset_ids=("missing",)),
            request_id="ai-missing",
        )

    assert error.value.code == "AI_DATASET_INVALID"
    assert context_service.calls == []
    assert gateway.calls == []


async def test_service_translates_missing_file_during_context_build() -> None:
    gateway = FakeGateway(response=ai_response())
    context_service = FakeContextService(
        contexts=contexts(),
        error=FileAssetNotFound("file-missing"),
    )
    service = AiService(
        gateway=gateway,
        context_service=context_service,
        dataset_repository=FakeDatasetRepository({"sales": sql_dataset_response()}),
        datasource_service=FakeDatasourceService(),
        registry=type("Registry", (), {"get": lambda self, _name: FakeConnector()})(),
    )

    with pytest.raises(AiAnalysisError) as error:
        await service.analyze(
            AiAnalysisRequest(question="分析销售趋势", dataset_ids=("sales",)),
            request_id="ai-file-missing",
        )

    assert error.value.code == "AI_DATASET_INVALID"
    assert gateway.calls == []


async def test_service_rejects_datasets_outside_request_before_preview() -> None:
    invalid = ai_response().model_copy(
        update={
            "plan": ai_response().plan.model_copy(update={"dataset_ids": ("other",)}),
        }
    )
    gateway = FakeGateway(response=invalid)
    datasource_service = FakeDatasourceService()
    service = AiService(
        gateway=gateway,
        context_service=FakeContextService(contexts=contexts()),
        dataset_repository=FakeDatasetRepository({"sales": sql_dataset_response()}),
        datasource_service=datasource_service,
        registry=type("Registry", (), {"get": lambda self, _name: FakeConnector()})(),
        max_context_rows=100,
    )

    with pytest.raises(AiAnalysisError) as error:
        await service.analyze(
            AiAnalysisRequest(
                question="分析最近几个月的销售趋势",
                dataset_ids=("sales",),
                mode="analysis",
            ),
            request_id="ai-req-2",
        )

    assert error.value.code == "AI_DATASET_INVALID"
    assert datasource_service.calls == []


async def test_service_exposes_gateway_health() -> None:
    service = AiService(
        gateway=FakeGateway(
            response=ai_response(),
            status=AiHealth(status="unconfigured", model=None),
        ),
    )

    assert service.health() == AiHealth(status="unconfigured", model=None)


async def test_service_generates_validated_screen_draft() -> None:
    gateway = FakeGateway(response=screen_plan_response())
    datasource_service = FakeDatasourceService()
    repository = FakeDatasetRepository({"sales": sql_dataset_response()})
    planning_runtime = FakePlanningRuntime()
    planning_service = RecordingPlanningService(
        DashboardPlanningService(
            dataset_repository=repository,
            runtime_service=planning_runtime,
        )
    )
    service = AiService(
        gateway=gateway,
        context_service=FakeContextService(contexts=contexts()),
        dataset_repository=repository,
        planning_service=planning_service,
        datasource_service=datasource_service,
        registry=type("Registry", (), {"get": lambda self, _name: FakeConnector()})(),
        max_context_rows=100,
    )

    response = await service.generate_screen(
        AiScreenRequest(
            question="生成销售运营大屏",
            dataset_ids=("sales",),
            theme="dark",
        ),
        request_id="screen-req-1",
    )

    assert response.document.theme.id == "datapulse-dark"
    assert response.document.components[0].type == "builtin.text"
    assert response.document.components[1].data_binding["chart_spec"]["dataset_id"] == "sales"
    assert response.plan is not None
    assert response.report is not None
    assert response.report.executed_count == 2
    assert [call.component_id for call in planning_runtime.calls] == [
        "sales-total",
        "sales-trend",
    ]
    assert datasource_service.calls == []
    assert "pixel coordinates" in str(gateway.calls[0]["user"])
    assert len(planning_service.compile_calls) == 1
    assert planning_service.compile_calls[0].plan == response.plan
    assert planning_service.compile_request_ids == ["screen-req-1"]


async def test_service_edits_plan_through_core_recompile_and_preserves_other_regions() -> None:
    previous_plan = DashboardPlan.model_validate(screen_plan_response()["plan"])
    repository = FakeDatasetRepository({"sales": sql_dataset_response()})
    planning_runtime = FakePlanningRuntime()
    core_service = DashboardPlanningService(
        dataset_repository=repository,
        runtime_service=planning_runtime,
    )
    compiled = await core_service.compile(DashboardPlanCompileRequest(plan=previous_plan))
    planning_runtime.calls.clear()
    planning_service = RecordingPlanningService(core_service)
    next_payload = previous_plan.model_dump(mode="json")
    next_payload["widgets"][1]["chart_type"] = "bar"
    gateway = FakeGateway(
        response={
            "plan": next_payload,
            "affected_region_ids": ("main",),
            "explanation": "已将趋势图改为柱状图。",
            "warnings": (),
        }
    )
    service = AiService(
        gateway=gateway,
        context_service=FakeContextService(contexts=contexts()),
        dataset_repository=repository,
        planning_service=planning_service,
    )

    response = await service.edit_screen(
        AiScreenEditRequest(
            question="把趋势图改成柱状图",
            plan=previous_plan,
            document=compiled.document,
            affected_region_ids=("main",),
        ),
        request_id="screen-edit-1",
    )

    previous_by_id = {component.id: component for component in compiled.document.components}
    next_by_id = {component.id: component for component in response.document.components}
    assert next_by_id["sales-total"] == previous_by_id["sales-total"]
    assert next_by_id["sales-trend"].type == "builtin.bar"
    assert response.affected_region_ids == ("main",)
    assert response.report.valid is True
    assert response.report.executed_count == 2
    assert [call.component_id for call in planning_runtime.calls] == [
        "sales-total",
        "sales-trend",
    ]
    assert len(planning_service.recompile_calls) == 1
    assert planning_service.recompile_request_ids == ["screen-edit-1"]
    assert "never publish" in str(gateway.calls[0]["system"])


async def test_service_rejects_screen_edit_datasets_and_scope_outside_original_plan() -> None:
    previous_plan = DashboardPlan.model_validate(screen_plan_response()["plan"])
    repository = FakeDatasetRepository({"sales": sql_dataset_response()})
    core_service = DashboardPlanningService(dataset_repository=repository)
    compiled = await core_service.compile(DashboardPlanCompileRequest(plan=previous_plan))
    planning_service = RecordingPlanningService(core_service)
    invalid_payload = previous_plan.model_dump(mode="json")
    invalid_payload["dataset_ids"] = ["other"]
    invalid_payload["widgets"][0]["dataset_id"] = "other"
    invalid_payload["widgets"][1]["dataset_id"] = "other"
    service = AiService(
        gateway=FakeGateway(
            response={
                "plan": invalid_payload,
                "affected_region_ids": ("summary", "main"),
                "explanation": "改用其他数据集。",
            }
        ),
        context_service=FakeContextService(contexts=contexts()),
        dataset_repository=repository,
        planning_service=planning_service,
    )

    with pytest.raises(AiAnalysisError) as caught:
        await service.edit_screen(
            AiScreenEditRequest(
                question="改用其他数据集",
                plan=previous_plan,
                document=compiled.document,
                affected_region_ids=("main",),
            ),
            request_id="screen-edit-invalid",
        )

    assert caught.value.code == "AI_DATASET_INVALID"
    assert planning_service.recompile_calls == []


async def test_service_applies_screen_timeout_to_edit_context_building() -> None:
    class SlowContextService(FakeContextService):
        async def build(
            self,
            dataset_ids: tuple[str, ...],
            *,
            max_rows: int,
            question: str | None = None,
        ) -> tuple[DatasetContext, ...]:
            await asyncio.sleep(0.05)
            return await super().build(dataset_ids, max_rows=max_rows, question=question)

    previous_plan = DashboardPlan.model_validate(screen_plan_response()["plan"])
    repository = FakeDatasetRepository({"sales": sql_dataset_response()})
    core_service = DashboardPlanningService(dataset_repository=repository)
    compiled = await core_service.compile(DashboardPlanCompileRequest(plan=previous_plan))
    service = AiService(
        gateway=FakeGateway(
            response={
                "plan": previous_plan.model_dump(mode="json"),
                "affected_region_ids": ("main",),
                "explanation": "未修改。",
            }
        ),
        context_service=SlowContextService(contexts=contexts()),
        dataset_repository=repository,
        planning_service=core_service,
        screen_timeout_seconds=0.01,
    )

    with pytest.raises(AiGatewayError) as caught:
        await service.edit_screen(
            AiScreenEditRequest(
                question="保持当前布局",
                plan=previous_plan,
                document=compiled.document,
                affected_region_ids=("main",),
            ),
            request_id="screen-edit-timeout",
        )

    assert caught.value.code == "AI_TIMEOUT"


async def test_service_keeps_editable_draft_when_one_chart_is_empty() -> None:
    repository = FakeDatasetRepository({"sales": sql_dataset_response()})
    planning_runtime = FakePlanningRuntime(row_counts=(1, 0))
    service = AiService(
        gateway=FakeGateway(response=screen_plan_response()),
        context_service=FakeContextService(contexts=contexts()),
        dataset_repository=repository,
        planning_service=DashboardPlanningService(
            dataset_repository=repository,
            runtime_service=planning_runtime,
        ),
    )

    response = await service.generate_screen(
        AiScreenRequest(question="生成销售运营大屏", dataset_ids=("sales",)),
        request_id="screen-empty",
    )

    by_id = {component.id: component for component in response.document.components}
    assert by_id["sales-total"].type == "builtin.kpi"
    assert by_id["sales-trend"].type == "builtin.panel"
    assert response.report is not None
    assert response.report.fallback_count == 1
    assert any("sales-trend" in warning for warning in response.warnings)


async def test_service_applies_independent_screen_timeout() -> None:
    class SlowContextService(FakeContextService):
        async def build(
            self,
            dataset_ids: tuple[str, ...],
            *,
            max_rows: int,
            question: str | None = None,
        ) -> tuple[DatasetContext, ...]:
            await asyncio.sleep(0.05)
            return await super().build(dataset_ids, max_rows=max_rows, question=question)

    service = AiService(
        gateway=FakeGateway(response=ai_response()),
        context_service=SlowContextService(contexts=contexts()),
        dataset_repository=FakeDatasetRepository({"sales": sql_dataset_response()}),
        screen_timeout_seconds=0.01,
    )

    with pytest.raises(AiGatewayError) as error:
        await service.generate_screen(
            AiScreenRequest(question="生成销售大屏", dataset_ids=("sales",)),
            request_id="screen-timeout",
        )

    assert error.value.code == "AI_TIMEOUT"
