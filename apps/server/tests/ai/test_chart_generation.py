from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from datapulse.ai.models import AiAnalysisError, AiHealth, DatasetContext
from datapulse.ai.service import AiService
from datapulse.contracts.ai import AiChartRequest
from datapulse.contracts.chart import ChartType
from datapulse.contracts.dataset import (
    CachePolicy,
    DatasetDefinition,
    DatasetField,
    DataType,
    RefreshPolicy,
    SqlQuery,
)
from datapulse.dataset.models import DatasetResponse
from datapulse.dataset.repository import DatasetNotFound
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
            query=SqlQuery(sql="SELECT region, amount FROM sales"),
            fields=(
                DatasetField(name="region", data_type=DataType.STRING),
                DatasetField(name="amount", data_type=DataType.NUMBER),
            ),
            parameters=(),
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
                {"name": "region", "data_type": "string"},
                {"name": "amount", "data_type": "number"},
            ),
            sample_rows=({"region": "north", "amount": 120},),
            summary="2 fields; 1 sample rows; 0 parameters.",
        ),
    )


def preview_result(request_id: str) -> QueryResult:
    return QueryResult(
        request_id=request_id,
        columns=(
            QueryColumn(name="region", data_type="string"),
            QueryColumn(name="amount", data_type="number"),
        ),
        rows=(("north", 120),),
        row_count=1,
        truncated=False,
        duration_ms=3,
    )


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
            {
                "system": system,
                "user": user,
                "response_model": response_model,
            }
        )
        return response_model.model_validate(self.payload)

    def health(self) -> AiHealth:
        return self.status

    def ensure_configured(self) -> None:
        return None


@dataclass
class FakeContextService:
    contexts: tuple[DatasetContext, ...]

    async def build(
        self,
        dataset_ids: tuple[str, ...],
        *,
        max_rows: int,
        question: str | None = None,
    ) -> tuple[DatasetContext, ...]:
        del question
        assert dataset_ids == ("sales",)
        assert max_rows == 100
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
        return preview_result(request_id)


def build_service(
    payload: dict[str, object],
) -> tuple[AiService, FakeDatasourceService, FakeGateway]:
    gateway = FakeGateway(payload=payload)
    datasource_service = FakeDatasourceService()
    service = AiService(
        gateway=gateway,
        context_service=FakeContextService(contexts=contexts()),
        dataset_repository=FakeDatasetRepository({"sales": sql_dataset_response()}),
        datasource_service=datasource_service,
        registry=type("Registry", (), {"get": lambda self, _name: FakeConnector()})(),
        max_context_rows=100,
    )
    return service, datasource_service, gateway


async def test_generate_chart_returns_validated_bar_chart_preview() -> None:
    service, datasource_service, gateway = build_service(
        {
            "chart_spec": {
                "dimensions": ("region",),
                "measures": ({"field": "amount", "aggregation": "sum"},),
                "filters": (),
                "sort": ({"field": "amount", "direction": "desc"},),
                "visual": {"type": "bar", "title": "区域销售额"},
            },
            "explanation": "按区域汇总销售额，柱状图最适合比较各区域表现。",
            "warnings": (),
        }
    )

    response = await service.generate_chart(
        AiChartRequest(
            question="按区域统计销售额",
            dataset_id="sales",
            target_component_type=ChartType.BAR,
        ),
        request_id="chart-req-1",
    )

    assert response.chart_spec.dataset_id == "sales"
    assert response.chart_spec.visual.type == "bar"
    assert response.chart_spec.limit == 1000
    assert response.preview.rows == (("north", 120),)
    assert datasource_service.calls[0]["trigger"] == "ai-chart"
    assert datasource_service.calls[0]["request"].max_rows == 1000
    assert "GROUP BY dataset_source.region" in datasource_service.calls[0]["request"].sql
    assert "allowed_fields:" in str(gateway.calls[0]["user"])


@pytest.mark.parametrize(
    ("payload", "chart_request"),
    [
        (
            {
                "chart_spec": {
                    "dimensions": ("missing",),
                    "measures": ({"field": "amount", "aggregation": "sum"},),
                    "visual": {"type": "bar"},
                },
                "explanation": "使用未知字段。",
                "warnings": (),
            },
            AiChartRequest(question="按区域统计销售额", dataset_id="sales"),
        ),
        (
            {
                "chart_spec": {
                    "dimensions": ("region",),
                    "measures": (),
                    "visual": {"type": "bar"},
                },
                "explanation": "缺少指标。",
                "warnings": (),
            },
            AiChartRequest(question="按区域统计销售额", dataset_id="sales"),
        ),
        (
            {
                "chart_spec": {
                    "dimensions": ("region",),
                    "measures": ({"field": "amount", "aggregation": "sum"},),
                    "visual": {"type": "line"},
                },
                "explanation": "图表类型与目标组件不一致。",
                "warnings": (),
            },
            AiChartRequest(
                question="按区域统计销售额",
                dataset_id="sales",
                target_component_type=ChartType.BAR,
            ),
        ),
        (
            {
                "chart_spec": {
                    "dimensions": ("region",),
                    "measures": ({"field": "amount", "aggregation": "sum"},),
                    "limit": 5001,
                    "visual": {"type": "bar"},
                },
                "explanation": "limit 超过支持范围。",
                "warnings": (),
            },
            AiChartRequest(question="按区域统计销售额", dataset_id="sales"),
        ),
        (
            {
                "chart_spec": {
                    "dimensions": ("region",),
                    "measures": ({"field": "amount", "aggregation": "sum"},),
                    "filters": (
                        {
                            "field": "region",
                            "operator": "in",
                            "value": {"kind": "literal", "value": "north"},
                        },
                    ),
                    "visual": {"type": "bar"},
                },
                "explanation": "非法过滤条件。",
                "warnings": (),
            },
            AiChartRequest(question="按区域统计销售额", dataset_id="sales"),
        ),
    ],
)
async def test_generate_chart_rejects_invalid_model_output(
    payload: dict[str, object],
    chart_request: AiChartRequest,
) -> None:
    service, datasource_service, _gateway = build_service(payload)

    with pytest.raises(AiAnalysisError) as error:
        await service.generate_chart(chart_request, request_id="chart-req-invalid")

    assert error.value.code == "AI_CHART_INVALID"
    assert datasource_service.calls == []
