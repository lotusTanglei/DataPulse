from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from datapulse.contracts.chart import (
    Aggregation,
    ChartSpec,
    ChartType,
    Measure,
    VisualSpec,
)
from datapulse.contracts.dashboard import (
    ComponentInstance,
    ComponentState,
    DashboardDocument,
    DashboardParameter,
    Frame,
)
from datapulse.contracts.dataset import (
    DatasetDefinition,
    DatasetField,
    DataType,
    SqlQuery,
)
from datapulse.dataset.models import DatasetResponse
from datapulse.query.models import QueryRequest, QueryResult
from datapulse.screen.repository import ScreenRepository
from datapulse.screen.runtime import (
    ComponentBindingInvalid,
    ComponentQueryRequest,
    ScreenComponentUnavailable,
    ScreenNotPublished,
    ScreenParameterInvalid,
    ScreenRuntimeService,
)

pytestmark = pytest.mark.anyio


def chart_spec() -> ChartSpec:
    return ChartSpec(
        dataset_id="sales",
        dimensions=("month",),
        measures=(Measure(field="amount", aggregation=Aggregation.SUM),),
        visual=VisualSpec(type=ChartType.LINE),
    )


def screen_document(
    *,
    hidden: bool = False,
    data_binding: dict[str, object] | None = None,
) -> DashboardDocument:
    return DashboardDocument(
        canvas={"width": 1920, "height": 1080},
        parameters=(
            DashboardParameter(
                id="region",
                name="region",
                data_type=DataType.STRING,
                default="east",
                allowed_values=("east", "west"),
            ),
        ),
        components=(
            ComponentInstance(
                id="line-1",
                type="builtin.line",
                frame=Frame(x=40, y=40, width=640, height=320),
                state=ComponentState(hidden=hidden),
                data_binding=data_binding
                if data_binding is not None
                else {"chart_spec": chart_spec().model_dump(mode="json")},
            ),
        ),
    )


@dataclass
class FakeDatasetRepository:
    response: DatasetResponse
    requested_ids: list[str] = field(default_factory=list)

    async def get(self, dataset_id: str) -> DatasetResponse:
        self.requested_ids.append(dataset_id)
        return self.response


@dataclass
class FakeDatasourceService:
    result: QueryResult
    requests: list[tuple[str, QueryRequest, str, str | None, str]] = field(default_factory=list)

    async def query(
        self,
        datasource_id: str,
        query_request: QueryRequest,
        *,
        request_id: str,
        dataset_id: str | None = None,
        trigger: str = "debug",
    ) -> QueryResult:
        self.requests.append((datasource_id, query_request, request_id, dataset_id, trigger))
        return self.result


def dataset_response() -> DatasetResponse:
    timestamp = datetime(2026, 7, 30, tzinfo=UTC)
    return DatasetResponse(
        id="sales",
        name="Sales",
        data_source_id="source-1",
        definition=DatasetDefinition(
            id="sales",
            name="Sales",
            data_source_id="source-1",
            query=SqlQuery(sql="SELECT month, amount, region FROM sales"),
            fields=(
                DatasetField(name="month", data_type=DataType.STRING),
                DatasetField(name="amount", data_type=DataType.NUMBER),
                DatasetField(name="region", data_type=DataType.STRING),
            ),
        ),
        created_at=timestamp,
        updated_at=timestamp,
    )


def query_result() -> QueryResult:
    return QueryResult(
        request_id="query-1",
        columns=(),
        rows=(),
        row_count=0,
        truncated=False,
        duration_ms=1,
    )


async def build_runtime(
    screen_repository: ScreenRepository,
    *,
    document: DashboardDocument | None = None,
) -> tuple[ScreenRuntimeService, FakeDatasourceService, str]:
    screen = await screen_repository.create(
        "Operations",
        document or screen_document(),
    )
    datasource_service = FakeDatasourceService(query_result())
    runtime = ScreenRuntimeService(
        screen_repository=screen_repository,
        dataset_repository=FakeDatasetRepository(dataset_response()),
        datasource_service=datasource_service,
    )
    return runtime, datasource_service, screen.id


async def test_runtime_authorizes_and_executes_stored_component_query(
    screen_repository: ScreenRepository,
) -> None:
    runtime, datasource_service, screen_id = await build_runtime(screen_repository)

    result = await runtime.query_draft_component(
        screen_id,
        ComponentQueryRequest(component_id="line-1", parameters={"region": "west"}),
        request_id="request-1",
    )

    assert result == query_result()
    datasource_id, request, request_id, dataset_id, trigger = datasource_service.requests[0]
    assert datasource_id == "source-1"
    assert request_id == "request-1"
    assert dataset_id == "sales"
    assert trigger == "screen-draft"
    assert "SELECT month, amount, region FROM sales" in request.sql
    assert "west" not in request.sql


@pytest.mark.parametrize(
    ("document", "component_id", "error_type"),
    [
        (screen_document(hidden=True), "line-1", ScreenComponentUnavailable),
        (screen_document(), "missing", ScreenComponentUnavailable),
        (screen_document(data_binding={}), "line-1", ComponentBindingInvalid),
    ],
)
async def test_runtime_rejects_unavailable_or_unbound_components(
    screen_repository: ScreenRepository,
    document: DashboardDocument,
    component_id: str,
    error_type: type[Exception],
) -> None:
    runtime, datasource_service, screen_id = await build_runtime(
        screen_repository,
        document=document,
    )

    with pytest.raises(error_type):
        await runtime.query_draft_component(
            screen_id,
            ComponentQueryRequest(component_id=component_id),
            request_id="request-1",
        )

    assert datasource_service.requests == []


async def test_runtime_validates_declared_parameter_values(
    screen_repository: ScreenRepository,
) -> None:
    runtime, datasource_service, screen_id = await build_runtime(screen_repository)

    with pytest.raises(ScreenParameterInvalid):
        await runtime.query_draft_component(
            screen_id,
            ComponentQueryRequest(component_id="line-1", parameters={"region": "north"}),
            request_id="request-1",
        )
    with pytest.raises(ScreenParameterInvalid):
        await runtime.query_draft_component(
            screen_id,
            ComponentQueryRequest(component_id="line-1", parameters={"unknown": "value"}),
            request_id="request-2",
        )

    assert datasource_service.requests == []


async def test_published_query_requires_a_published_document(
    screen_repository: ScreenRepository,
) -> None:
    runtime, datasource_service, screen_id = await build_runtime(screen_repository)

    with pytest.raises(ScreenNotPublished):
        await runtime.query_published_component(
            screen_id,
            ComponentQueryRequest(component_id="line-1"),
            request_id="request-1",
            trigger="screen-player",
        )

    assert datasource_service.requests == []
