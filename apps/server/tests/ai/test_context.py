from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from datapulse.ai.context import DatasetContextService
from datapulse.contracts.dataset import (
    CachePolicy,
    DatasetDefinition,
    DatasetField,
    DataType,
    RefreshPolicy,
    SqlQuery,
)
from datapulse.dataset.models import DatasetResponse
from datapulse.dataset.profile import DatasetFieldProfile, DatasetProfile, FieldRole
from datapulse.query.models import QueryColumn, QueryRequest, QueryResult

pytestmark = pytest.mark.anyio


def dataset_response() -> DatasetResponse:
    fields = tuple(
        DatasetField(name=f"field_{index}", data_type=DataType.STRING) for index in range(60)
    )
    return DatasetResponse(
        id="sales",
        name="销售数据集",
        data_source_id="source-1",
        definition=DatasetDefinition(
            id="sales",
            name="销售数据集",
            data_source_id="source-1",
            query=SqlQuery(sql="SELECT * FROM sales"),
            fields=fields,
            parameters=(),
            cache=CachePolicy(),
            refresh=RefreshPolicy(),
            max_rows=5000,
            timeout_seconds=30,
        ),
        created_at="2026-08-01T00:00:00Z",
        updated_at="2026-08-01T00:00:00Z",
    )


@dataclass
class FakeDatasetRepository:
    dataset: DatasetResponse

    async def get(self, dataset_id: str) -> DatasetResponse:
        assert dataset_id == self.dataset.id
        return self.dataset


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
    calls: list[QueryRequest] = field(default_factory=list)

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
        del datasource_id, request_id, dataset_id, trigger
        self.calls.append(request)
        long_text = "x" * 160
        columns = tuple(
            QueryColumn(name=f"field_{index}", data_type="string") for index in range(60)
        )
        rows = tuple(
            tuple(long_text if index == 0 else f"value-{row}-{index}" for index in range(60))
            for row in range(3)
        )
        return QueryResult(
            request_id="ctx-1",
            columns=columns,
            rows=rows,
            row_count=3,
            truncated=False,
            duration_ms=5,
        )


@dataclass
class FakeProfileService:
    async def profile(self, dataset_id: str, *, max_rows: int = 5000) -> DatasetProfile:
        assert dataset_id == "sales"
        return DatasetProfile(
            dataset_id="sales",
            name="销售数据集",
            row_count=1000,
            sampled=True,
            fields=(
                DatasetFieldProfile(
                    name="region",
                    data_type="string",
                    role=FieldRole.DIMENSION,
                    nullable=False,
                    cardinality=5,
                    unique_count=5,
                    uniqueness_ratio=0.5,
                    sample_values=("华东",),
                ),
                DatasetFieldProfile(
                    name="amount",
                    data_type="number",
                    role=FieldRole.MEASURE,
                    nullable=False,
                    cardinality=100,
                    unique_count=100,
                    uniqueness_ratio=0.1,
                    sample_values=(10,),
                ),
                DatasetFieldProfile(
                    name="notes",
                    data_type="string",
                    role=FieldRole.TEXT,
                    nullable=True,
                    cardinality=1000,
                    unique_count=1000,
                    uniqueness_ratio=1,
                    sample_values=("内部备注",),
                ),
            ),
            candidate_time_fields=(),
            measure_candidates=("amount",),
            geographic_fields=(),
            suspected_primary_key=None,
            time_coverage=None,
        )


async def test_context_service_limits_fields_rows_and_truncates_strings() -> None:
    datasource_service = FakeDatasourceService()
    service = DatasetContextService(
        dataset_repository=FakeDatasetRepository(dataset_response()),
        datasource_service=datasource_service,
        registry=type("Registry", (), {"get": lambda self, _name: FakeConnector()})(),
    )

    contexts = await service.build(("sales",), max_rows=2)

    assert len(contexts) == 1
    context = contexts[0]
    assert context.dataset_id == "sales"
    assert len(context.fields) == 50
    assert len(context.sample_rows) == 2
    assert str(context.sample_rows[0]["field_0"]).endswith("...")
    assert datasource_service.calls[0].max_rows == 2
    assert context.summary == "50 fields; 2 sample rows; 0 parameters."


async def test_context_service_enforces_serialized_character_budget() -> None:
    datasource_service = FakeDatasourceService()
    service = DatasetContextService(
        dataset_repository=FakeDatasetRepository(dataset_response()),
        datasource_service=datasource_service,
        registry=type("Registry", (), {"get": lambda self, _name: FakeConnector()})(),
        max_context_chars=600,
    )

    context = (await service.build(("sales",), max_rows=10))[0]

    assert len(context.fields) < 50
    assert len(context.sample_rows) <= 2
    assert "budget" in context.summary


async def test_context_defaults_to_profile_summary_and_filters_by_question() -> None:
    datasource_service = FakeDatasourceService()
    service = DatasetContextService(
        dataset_repository=FakeDatasetRepository(dataset_response()),
        datasource_service=datasource_service,
        registry=type("Registry", (), {"get": lambda self, _name: FakeConnector()})(),
        profile_service=FakeProfileService(),
    )

    context = (await service.build(("sales",), max_rows=10, question="amount"))[0]

    assert [field.name for field in context.fields] == ["amount"]
    assert context.fields[0].role == "measure"
    assert context.sample_rows == ()
    assert "1000 rows" in context.profile_summary
    assert datasource_service.calls == []


async def test_context_can_request_samples_after_profile_selection() -> None:
    datasource_service = FakeDatasourceService()
    service = DatasetContextService(
        dataset_repository=FakeDatasetRepository(dataset_response()),
        datasource_service=datasource_service,
        registry=type("Registry", (), {"get": lambda self, _name: FakeConnector()})(),
        profile_service=FakeProfileService(),
    )

    context = (
        await service.build(
            ("sales",),
            max_rows=2,
            question="amount",
            include_samples=True,
        )
    )[0]

    assert len(context.sample_rows) == 2
    assert datasource_service.calls[0].max_rows == 2
