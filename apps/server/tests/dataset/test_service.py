from dataclasses import dataclass, field
from pathlib import Path

import pytest

from datapulse.contracts.dataset import DataType, FileFormat
from datapulse.contracts.filedata import FileDatasetCreate
from datapulse.dataset.models import DatasetCreate, DatasetUpdate
from datapulse.dataset.repository import DatasetRepository
from datapulse.dataset.service import DatasetService, DatasetUpdateInvalid
from datapulse.datasource.models import DatasourceCreate, SQLiteConfig
from datapulse.datasource.registry import ConnectorRegistry
from datapulse.datasource.repository import DatasourceNotFound, DatasourceRepository
from datapulse.filedata.repository import FileAssetRepository
from datapulse.query.models import QueryColumn, QueryRequest, QueryResult
from datapulse.query.safety import QueryValidationError

pytestmark = pytest.mark.anyio


@dataclass
class DialectConnector:
    type: str = "sqlite"
    dialect: str = "sqlite"


@dataclass
class FakeDatasourceService:
    source: object
    result: QueryResult
    error: Exception | None = None
    requests: list[QueryRequest] = field(default_factory=list)

    async def get(self, datasource_id: str) -> object:
        if datasource_id != self.source.id:
            raise DatasourceNotFound(datasource_id)
        return self.source

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
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.result


def preview_result() -> QueryResult:
    return QueryResult(
        request_id="preview-1",
        columns=(
            QueryColumn(name="month", data_type="string"),
            QueryColumn(name="sales", data_type="decimal"),
        ),
        rows=(("2026-01", 150),),
        row_count=1,
        truncated=False,
        duration_ms=3,
    )


async def build_service(
    datasource_repository: DatasourceRepository,
    dataset_repository: DatasetRepository,
    *,
    error: Exception | None = None,
    file_asset_repository: FileAssetRepository | None = None,
) -> tuple[DatasetService, FakeDatasourceService]:
    try:
        source = await datasource_repository.get("source-1")
    except DatasourceNotFound:
        source = await datasource_repository.create(
            "source-1",
            DatasourceCreate(name="Sales", config=SQLiteConfig(path="sales.db")),
        )
    datasource_service = FakeDatasourceService(
        source=source,
        result=preview_result(),
        error=error,
    )
    return (
        DatasetService(
            repository=dataset_repository,
            datasource_service=datasource_service,
            registry=ConnectorRegistry([DialectConnector()]),
            file_asset_repository=file_asset_repository,
            id_factory=lambda: "dataset-1",
        ),
        datasource_service,
    )


async def test_save_query_previews_infers_fields_and_persists_definition(
    datasource_repository: DatasourceRepository,
    metadata_session_factory: object,
) -> None:
    repository = DatasetRepository(metadata_session_factory)
    service, datasource_service = await build_service(
        datasource_repository,
        repository,
    )

    created = await service.create(
        DatasetCreate(
            name="Monthly sales",
            data_source_id="source-1",
            sql="SELECT month, SUM(amount) AS sales FROM sales GROUP BY month",
        ),
        request_id="save-1",
    )

    assert created.definition.schema_version == 1
    assert created.definition.query.kind == "sql"
    assert created.definition.fields[0].name == "month"
    assert created.definition.fields[0].data_type is DataType.STRING
    assert created.definition.fields[1].name == "sales"
    assert created.definition.fields[1].data_type is DataType.NUMBER
    assert datasource_service.requests[0].sql == created.definition.query.sql
    assert await repository.list() == (created,)


async def test_invalid_source_unsafe_sql_and_preview_failure_do_not_persist(
    datasource_repository: DatasourceRepository,
    metadata_session_factory: object,
) -> None:
    repository = DatasetRepository(metadata_session_factory)
    service, datasource_service = await build_service(
        datasource_repository,
        repository,
    )
    payload = DatasetCreate(
        name="Monthly sales",
        data_source_id="source-1",
        sql="DELETE FROM sales",
    )

    with pytest.raises(QueryValidationError):
        await service.create(payload, request_id="unsafe-1")
    assert datasource_service.requests == []
    assert await repository.list() == ()

    missing = payload.model_copy(
        update={"data_source_id": "missing", "sql": "SELECT * FROM sales"}
    )
    with pytest.raises(DatasourceNotFound):
        await service.create(missing, request_id="missing-1")
    assert await repository.list() == ()

    failing_service, _ = await build_service(
        datasource_repository,
        repository,
        error=RuntimeError("preview failed"),
    )
    with pytest.raises(RuntimeError, match="preview failed"):
        await failing_service.create(
            payload.model_copy(update={"sql": "SELECT * FROM sales"}),
            request_id="failed-1",
        )
    assert await repository.list() == ()


async def test_file_update_reparses_fields_and_rejects_sql_configuration(
    datasource_repository: DatasourceRepository,
    metadata_session_factory: object,
    tmp_path: Path,
) -> None:
    repository = DatasetRepository(metadata_session_factory)
    file_repository = FileAssetRepository(metadata_session_factory)
    file_path = tmp_path / "sales.csv"
    file_path.write_text("region,amount\nnorth,10\nsouth,20\n", encoding="utf-8")
    await file_repository.create(
        asset_id="asset-1",
        original_name="sales.csv",
        format=FileFormat.CSV,
        mime_type="text/csv",
        sha256="a" * 64,
        size_bytes=file_path.stat().st_size,
        storage_path=str(file_path),
        row_count=2,
        fields_json=[],
    )
    service, _ = await build_service(
        datasource_repository,
        repository,
        file_asset_repository=file_repository,
    )
    created = await service.create_file(
        FileDatasetCreate(name="Sales file", file_asset_id="asset-1"),
        request_id="file-create-1",
    )

    updated = await service.update(
        created.id,
        DatasetUpdate(name="Sales renamed", max_rows=100, timeout_seconds=12),
        request_id="file-update-1",
    )

    assert updated.name == "Sales renamed"
    assert updated.definition.max_rows == 100
    assert updated.definition.timeout_seconds == 12
    assert [field.name for field in updated.definition.fields] == ["region", "amount"]
    assert updated.definition.query == created.definition.query

    with pytest.raises(DatasetUpdateInvalid):
        await service.update(
            created.id,
            DatasetUpdate(sql="SELECT * FROM dataset_source"),
            request_id="file-update-sql",
        )
    with pytest.raises(DatasetUpdateInvalid):
        await service.update(
            created.id,
            DatasetUpdate(parameters=()),
            request_id="file-update-parameters",
        )
