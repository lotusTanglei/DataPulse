from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from datapulse.ai.models import AiAnalysisError, AiGatewayError, AiHealth, DatasetContext
from datapulse.ai.service import AiService
from datapulse.contracts.ai import AiAnalysisDraft, AiAnalysisRequest, AiScreenRequest
from datapulse.contracts.chart import ChartSpec
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
    ) -> tuple[DatasetContext, ...]:
        self.calls.append({"dataset_ids": dataset_ids, "max_rows": max_rows})
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
    assert context_service.calls == [{"dataset_ids": ("sales",), "max_rows": 100}]
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
    gateway = FakeGateway(
        response={
            "document": {
                "components": [
                    {
                        "type": "builtin.text",
                        "frame": {"x": 40, "y": 24, "width": 720, "height": 80},
                        "props": {"text": "销售运营大屏"},
                    },
                    {
                        "type": "builtin.line",
                        "frame": {"x": 40, "y": 128, "width": 760, "height": 320},
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
                                "visual": {"type": "line", "title": "销售趋势"},
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
                    }
                ],
            },
            "explanation": "生成销售运营大屏草稿。",
            "warnings": (),
        }
    )
    service = AiService(
        gateway=gateway,
        context_service=FakeContextService(contexts=contexts()),
        dataset_repository=FakeDatasetRepository({"sales": sql_dataset_response()}),
        datasource_service=FakeDatasourceService(),
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
    assert "allowed_component_types:" in str(gateway.calls[0]["user"])
