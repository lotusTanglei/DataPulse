from dataclasses import dataclass, field
from pathlib import Path

import pytest

from datapulse.ai.models import DatasetContext
from datapulse.ai.service import AiService
from datapulse.contracts.ai import AiScreenRequest
from datapulse.contracts.dataset import DatasetDefinition
from datapulse.dataset.models import DatasetResponse
from datapulse.query.models import QueryColumn, QueryResult
from datapulse.screen.planning_service import DashboardPlanningService
from datapulse.screen.runtime import ScreenRuntimeService

pytestmark = pytest.mark.anyio


def _dataset(
    dataset_id: str,
    name: str,
    query: dict[str, object],
    *,
    data_source_id: str | None,
    dimension: str,
    measure: str,
) -> DatasetResponse:
    definition = DatasetDefinition.model_validate(
        {
            "id": dataset_id,
            "name": name,
            "data_source_id": data_source_id,
            "query": query,
            "fields": (
                {"name": dimension, "data_type": "string"},
                {"name": measure, "data_type": "number"},
            ),
        }
    )
    return DatasetResponse(
        id=dataset_id,
        name=name,
        data_source_id=data_source_id,
        definition=definition,
        created_at="2026-09-23T00:00:00Z",
        updated_at="2026-09-23T00:00:00Z",
    )


def _datasets(
    scenario: str,
    *,
    dimension: str,
    measure: str,
) -> dict[str, DatasetResponse]:
    return {
        f"{scenario}-warehouse": _dataset(
            f"{scenario}-warehouse",
            f"{scenario} 主库数据",
            {"kind": "sql", "sql": f"SELECT {dimension}, {measure} FROM {scenario}_metrics"},
            data_source_id=f"{scenario}-warehouse-source",
            dimension=dimension,
            measure=measure,
        ),
        f"{scenario}-excel": _dataset(
            f"{scenario}-excel",
            f"{scenario} Excel 计划",
            {
                "kind": "file",
                "asset_id": f"{scenario}-targets.xlsx",
                "format": "excel",
                "sheet_name": "目标",
            },
            data_source_id=None,
            dimension=dimension,
            measure=measure,
        ),
        f"{scenario}-api": _dataset(
            f"{scenario}-api",
            f"{scenario} 实时接口",
            {"kind": "rest", "url": f"https://api.example.com/{scenario}"},
            data_source_id=f"{scenario}-api-source",
            dimension=dimension,
            measure=measure,
        ),
    }


def _contexts(
    datasets: dict[str, DatasetResponse],
    *,
    dimension: str,
    measure: str,
) -> tuple[DatasetContext, ...]:
    return tuple(
        DatasetContext(
            dataset_id=dataset.id,
            name=dataset.name,
            fields=(
                {"name": dimension, "data_type": "string"},
                {"name": measure, "data_type": "number"},
            ),
            sample_rows=({dimension: "样例", measure: 100},),
            summary="2 fields; 1 sample row.",
        )
        for dataset in datasets.values()
    )


def _screen_response(
    title: str,
    template: str,
    datasets: dict[str, DatasetResponse],
    *,
    dimension: str,
    measure: str,
) -> dict[str, object]:
    return {
        "plan": {
            "title": title,
            "audience": "经营负责人",
            "narrative": "同时展示主库、Excel 和接口指标。",
            "dataset_ids": tuple(datasets),
            "layout": {"template": template},
            "regions": ({"id": "main", "kind": "main"},),
            "widgets": tuple(
                {
                    "id": f"{dataset_id}-chart",
                    "title": name,
                    "intent": f"展示{name}",
                    "region_id": "main",
                    "dataset_id": dataset_id,
                    "chart_type": "bar",
                    "dimensions": (dimension,),
                    "measures": ({"field": measure, "aggregation": "sum"},),
                }
                for dataset_id, name in (
                    (dataset.id, dataset.name) for dataset in datasets.values()
                )
            ),
        },
        "explanation": "已按来源编排三个组件。",
        "warnings": (),
    }


@dataclass
class FakeGateway:
    response: dict[str, object]

    def ensure_configured(self) -> None:
        return None

    async def complete_json(self, *, system: str, user: str, response_model):
        del system, user
        return response_model.model_validate(self.response)


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
        del max_rows, question
        contexts = {context.dataset_id: context for context in self.contexts}
        return tuple(contexts[dataset_id] for dataset_id in dataset_ids)


@dataclass
class FakeDatasetRepository:
    datasets: dict[str, DatasetResponse]

    async def get(self, dataset_id: str) -> DatasetResponse:
        return self.datasets[dataset_id]


@dataclass
class FakeDatasourceService:
    sql_calls: list[str] = field(default_factory=list)
    rest_calls: list[str] = field(default_factory=list)

    async def dialect(self, datasource_id: str) -> str:
        del datasource_id
        return "sqlite"

    async def query(self, datasource_id: str, request, **kwargs) -> QueryResult:
        del request, kwargs
        self.sql_calls.append(datasource_id)
        return _result("sql")

    async def rest_query(self, datasource_id: str, query, **kwargs) -> QueryResult:
        del query, kwargs
        self.rest_calls.append(datasource_id)
        return _result("rest")


@dataclass
class FakeFileAssetRepository:
    async def get(self, asset_id: str):
        return type("Asset", (), {"storage_path": f"/fixtures/{asset_id}"})()


@dataclass
class FakeFileQueryService:
    calls: list[str] = field(default_factory=list)

    async def query(self, *, dataset: DatasetDefinition, **kwargs) -> QueryResult:
        del kwargs
        self.calls.append(dataset.id)
        return _result("file")


def _result(request_id: str) -> QueryResult:
    return QueryResult(
        request_id=request_id,
        columns=(
            QueryColumn(name="category", data_type="string"),
            QueryColumn(name="amount", data_type="number"),
        ),
        rows=(("华东", 100),),
        row_count=1,
        truncated=False,
        duration_ms=1,
    )


@pytest.mark.parametrize(
    ("scenario", "title", "template", "dimension", "measure"),
    (
        ("business", "经营驾驶舱", "executive-overview", "region", "revenue"),
        ("sales", "销售对比大屏", "comparison-board", "product", "sales_amount"),
        ("equipment", "设备运营状态墙", "status-wall", "device", "alarm_count"),
    ),
)
async def test_sql_excel_and_http_api_generate_one_editable_multisource_screen(
    monkeypatch: pytest.MonkeyPatch,
    scenario: str,
    title: str,
    template: str,
    dimension: str,
    measure: str,
) -> None:
    async def fake_parse_file(*args, **kwargs):
        del args, kwargs
        return type("Parsed", (), {"normalized_path": Path("/tmp/targets.parquet")})()

    monkeypatch.setattr("datapulse.screen.runtime.parse_file", fake_parse_file)
    datasource_service = FakeDatasourceService()
    file_query_service = FakeFileQueryService()
    datasets = _datasets(scenario, dimension=dimension, measure=measure)
    repository = FakeDatasetRepository(datasets)
    runtime_service = ScreenRuntimeService(
        screen_repository=object(),
        dataset_repository=repository,
        datasource_service=datasource_service,
        file_asset_repository=FakeFileAssetRepository(),
        file_query_service=file_query_service,
    )
    service = AiService(
        gateway=FakeGateway(
            _screen_response(
                title,
                template,
                datasets,
                dimension=dimension,
                measure=measure,
            )
        ),
        context_service=FakeContextService(
            _contexts(datasets, dimension=dimension, measure=measure)
        ),
        dataset_repository=repository,
        planning_service=DashboardPlanningService(
            dataset_repository=repository,
            runtime_service=runtime_service,
        ),
    )

    response = await service.generate_screen(
        AiScreenRequest(
            question=f"生成{title}",
            dataset_ids=tuple(datasets),
        ),
        request_id=f"multisource-{template}",
    )

    chart_specs = [
        component.data_binding["chart_spec"]
        for component in response.document.components
        if "chart_spec" in component.data_binding
    ]
    assert {spec["dataset_id"] for spec in chart_specs} == set(datasets)
    assert all(isinstance(spec["dataset_id"], str) for spec in chart_specs)
    assert response.report.executed_count == 3
    assert response.report.fallback_count == 0
    assert datasource_service.sql_calls == [f"{scenario}-warehouse-source"]
    assert datasource_service.rest_calls == [f"{scenario}-api-source"]
    assert file_query_service.calls == [f"{scenario}-excel"]
