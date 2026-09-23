from dataclasses import dataclass

import pytest

from datapulse.contracts.dataset import (
    CachePolicy,
    DatasetDefinition,
    DatasetField,
    DataType,
    RefreshPolicy,
    SqlQuery,
)
from datapulse.dataset.models import DatasetResponse
from datapulse.dataset.profile import DatasetProfilePatch, DatasetProfileService, FieldRole
from datapulse.query.models import QueryColumn, QueryResult

pytestmark = pytest.mark.anyio


def dataset() -> DatasetResponse:
    return DatasetResponse(
        id="sales",
        name="销售数据",
        data_source_id="source-1",
        definition=DatasetDefinition(
            id="sales",
            name="销售数据",
            data_source_id="source-1",
            query=SqlQuery(sql="SELECT order_id, region, amount, happened_at FROM sales"),
            fields=(
                DatasetField(name="order_id", data_type=DataType.STRING),
                DatasetField(name="region", data_type=DataType.STRING),
                DatasetField(name="province", data_type=DataType.STRING),
                DatasetField(name="amount", data_type=DataType.NUMBER),
                DatasetField(name="happened_at", data_type=DataType.DATETIME),
            ),
            cache=CachePolicy(),
            refresh=RefreshPolicy(),
            max_rows=5000,
            timeout_seconds=30,
        ),
        created_at="2026-09-22T00:00:00Z",
        updated_at="2026-09-22T00:00:00Z",
    )


@dataclass
class FakeRepository:
    value: DatasetResponse

    async def get(self, dataset_id: str) -> DatasetResponse:
        assert dataset_id == self.value.id
        return self.value

    async def update(self, dataset_id: str, definition: DatasetDefinition) -> DatasetResponse:
        assert dataset_id == self.value.id
        self.value = self.value.model_copy(update={"definition": definition})
        return self.value


@dataclass
class FakeDatasource:
    async def get(self, datasource_id: str) -> object:
        return type("Source", (), {"config": type("Config", (), {"type": "sqlite"})()})()

    async def query(self, *args, **kwargs) -> QueryResult:
        return QueryResult(
            request_id="profile-1",
            columns=(
                QueryColumn(name="order_id", data_type="string"),
                QueryColumn(name="region", data_type="string"),
                QueryColumn(name="province", data_type="string"),
                QueryColumn(name="amount", data_type="decimal"),
                QueryColumn(name="happened_at", data_type="datetime"),
            ),
            rows=(
                ("A-1", "华东", "江苏", 10.5, "2026-09-22T08:30:00"),
                ("A-2", "华东", "江苏", 20, "2026-09-23T08:30:00"),
                ("A-3", "华南", "浙江", 30, "2026-09-24T08:30:00"),
            ),
            row_count=3,
            truncated=False,
            duration_ms=1,
        )


@dataclass
class FakeRegistry:
    def get(self, _name: str) -> object:
        return type("Connector", (), {"dialect": "sqlite"})()


async def test_profile_service_returns_stats_and_deterministic_roles() -> None:
    service = DatasetProfileService(
        dataset_repository=FakeRepository(dataset()),
        datasource_service=FakeDatasource(),
        registry=FakeRegistry(),
    )

    profile = await service.profile("sales")

    by_name = {field.name: field for field in profile.fields}
    assert profile.dataset_id == "sales"
    assert profile.row_count == 3
    assert by_name["order_id"].role is FieldRole.IDENTIFIER
    assert by_name["order_id"].unique_count == 3
    assert by_name["region"].role is FieldRole.DIMENSION
    assert by_name["province"].role is FieldRole.GEOGRAPHY
    assert by_name["amount"].role is FieldRole.MEASURE
    assert by_name["amount"].null_rate == 0
    assert by_name["amount"].min == 10.5
    assert by_name["amount"].max == 30
    assert by_name["region"].top_values[0].value == "华东"
    assert by_name["region"].top_values[0].count == 2
    assert by_name["happened_at"].role is FieldRole.TEMPORAL
    assert profile.suspected_primary_key == "order_id"
    assert profile.candidate_time_fields == ("happened_at",)
    assert profile.measure_candidates == ("amount",)
    assert profile.geographic_fields == ("province",)
    assert profile.time_coverage == ("2026-09-22T08:30:00", "2026-09-24T08:30:00")


async def test_profile_overrides_are_applied_after_recomputation() -> None:
    service = DatasetProfileService(
        dataset_repository=FakeRepository(dataset()),
        datasource_service=FakeDatasource(),
        registry=FakeRegistry(),
    )

    profile = await service.profile(
        "sales",
        overrides={"region": {"role": FieldRole.TEXT, "data_type": DataType.STRING}},
    )

    assert next(field for field in profile.fields if field.name == "region").role is FieldRole.TEXT


async def test_profile_corrections_persist_display_metadata() -> None:
    repository = FakeRepository(dataset())
    service = DatasetProfileService(
        dataset_repository=repository,
        datasource_service=FakeDatasource(),
        registry=FakeRegistry(),
    )

    profile = await service.update(
        "sales",
        DatasetProfilePatch(
            fields=[
                {
                    "name": "amount",
                    "default_aggregation": "avg",
                    "unit": "元",
                    "display_name": "销售额",
                }
            ]
        ),
    )

    amount = next(field for field in profile.fields if field.name == "amount")
    assert amount.default_aggregation == "avg"
    assert amount.unit == "元"
    assert amount.display_name == "销售额"
    assert repository.value.definition.profile_overrides[0].unit == "元"
