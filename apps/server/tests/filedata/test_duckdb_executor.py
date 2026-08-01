import time
from pathlib import Path

import pytest

from datapulse.contracts.chart import Aggregation, ChartSpec, ChartType, Measure, VisualSpec
from datapulse.contracts.dataset import DatasetDefinition, DatasetField, DataType, FileQuery, FileFormat
from datapulse.filedata.duckdb_executor import DuckDBExecutor, FileQueryExecutionError
from datapulse.filedata.query import FileDatasetQueryService, FileQueryCompiler
from datapulse.screen.chart_query import ChartQueryInvalid
from datapulse.settings import Settings

pytestmark = pytest.mark.anyio


def dataset_definition() -> DatasetDefinition:
    return DatasetDefinition(
        id="sales",
        name="Sales",
        data_source_id=None,
        query=FileQuery(asset_id="asset-1", format=FileFormat.CSV),
        fields=(
            DatasetField(name="region", data_type=DataType.STRING),
            DatasetField(name="amount", data_type=DataType.NUMBER),
        ),
    )


def chart_spec(*, limit: int = 1000) -> ChartSpec:
    return ChartSpec(
        dataset_id="sales",
        dimensions=("region",),
        measures=(Measure(field="amount", aggregation=Aggregation.SUM),),
        limit=limit,
        visual=VisualSpec(type=ChartType.BAR),
    )


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        data_dir=tmp_path,
        file_max_rows=2,
        duckdb_timeout_seconds=1,
    )


@pytest.fixture
def source_path(settings: Settings) -> Path:
    path = settings.resolved_files_dir() / "asset-1"
    path.mkdir(parents=True, exist_ok=True)
    source = path / "source.csv"
    source.write_text("region,amount\nnorth,10\nsouth,20\nwest,30\n", encoding="utf-8")
    return source


async def test_query_service_compiles_parameterized_query(
    settings: Settings,
    source_path: Path,
) -> None:
    service = FileDatasetQueryService(
        compiler=FileQueryCompiler(),
        executor=DuckDBExecutor(settings),
    )

    result = await service.query(
        dataset=dataset_definition(),
        chart_spec=chart_spec(limit=2),
        parameters={},
        request_id="req-1",
        source_path=source_path,
    )

    assert result.request_id == "req-1"
    assert result.row_count == 2
    assert result.truncated is False
    assert result.columns[0].name == "region"


def test_compiler_rejects_unknown_fields() -> None:
    with pytest.raises(ChartQueryInvalid) as captured:
        FileQueryCompiler().compile(
            spec=chart_spec().model_copy(update={"dimensions": ("missing",)}),
            dataset=dataset_definition(),
            source_path=Path("/tmp/source.csv"),
            parameters={},
        )

    assert captured.value.code == "CHART_FIELD_UNKNOWN"


async def test_executor_rejects_source_outside_controlled_directory(settings: Settings) -> None:
    executor = DuckDBExecutor(settings)
    outside = settings.data_dir / "outside.csv"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("region,amount\nnorth,10\n", encoding="utf-8")

    with pytest.raises(FileQueryExecutionError) as captured:
        await executor.execute(
            "SELECT region, amount FROM dataset_source LIMIT 10",
            {},
            source_path=outside,
            request_id="req-1",
            timeout_seconds=1,
            max_rows=10,
        )

    assert captured.value.code == "FILE_NOT_FOUND"


async def test_executor_rejects_filesystem_functions_in_sql(
    settings: Settings,
    source_path: Path,
) -> None:
    executor = DuckDBExecutor(settings)

    with pytest.raises(FileQueryExecutionError) as captured:
        await executor.execute(
            "SELECT * FROM read_csv_auto('/etc/passwd')",
            {},
            source_path=source_path,
            request_id="req-1",
            timeout_seconds=1,
            max_rows=10,
        )

    assert captured.value.code == "FILE_QUERY_INVALID"


async def test_executor_enforces_max_rows_with_truncation(
    settings: Settings,
    source_path: Path,
) -> None:
    executor = DuckDBExecutor(settings)

    result = await executor.execute(
        "SELECT region, amount FROM dataset_source ORDER BY amount",
        (),
        source_path=source_path,
        request_id="req-1",
        timeout_seconds=1,
        max_rows=2,
    )

    assert result.row_count == 2
    assert result.truncated is True


async def test_executor_returns_timeout_error_when_query_exceeds_limit(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    source_path: Path,
) -> None:
    executor = DuckDBExecutor(settings)

    def slow_execute(*args, **kwargs):
        del args, kwargs
        time.sleep(0.05)
        return (), (), False

    monkeypatch.setattr(executor, "_execute_sync", slow_execute)

    with pytest.raises(FileQueryExecutionError) as captured:
        await executor.execute(
            "SELECT region, amount FROM dataset_source",
            {},
            source_path=source_path,
            request_id="req-1",
            timeout_seconds=0.01,
            max_rows=10,
        )

    assert captured.value.code == "FILE_QUERY_TIMEOUT"
