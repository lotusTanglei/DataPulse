import asyncio
import sys
from datetime import UTC, datetime

import pytest

from datapulse.contracts.dataset import FileFormat
from datapulse.errors import DataPulseError
from datapulse.filedata.duckdb_executor import DuckDBExecutor
from datapulse.filedata.models import StoredFileAsset
from datapulse.filedata.query import FileDatasetQueryService, FileQueryCompiler
from datapulse.operations.processing import run_processor
from datapulse.screen.runtime import ScreenDocumentQueryRequest, ScreenRuntimeService
from datapulse.settings import Settings
from tests.screen.test_runtime import (
    FakeDatasetRepository,
    FakeDatasourceService,
    FakeFileAssetRepository,
    chart_spec,
    file_dataset_response,
    query_result,
    screen_document,
)

pytestmark = pytest.mark.anyio


def file_runtime(tmp_path, *, invalid=False):
    source = tmp_path / "files/asset-1/source.csv"
    source.parent.mkdir(parents=True)
    source.write_text("invalid json" if invalid else "month,amount\n2026-01,10\n")
    dataset = file_dataset_response()
    if invalid:
        dataset = dataset.model_copy(
            update={
                "definition": dataset.definition.model_copy(
                    update={
                        "query": dataset.definition.query.model_copy(
                            update={"format": FileFormat.JSON}
                        )
                    }
                )
            }
        )
    runtime = ScreenRuntimeService(
        screen_repository=None,
        dataset_repository=FakeDatasetRepository(dataset),
        datasource_service=FakeDatasourceService(query_result()),
        file_asset_repository=FakeFileAssetRepository(
            StoredFileAsset(
                id="asset-1",
                original_name=source.name,
                format=dataset.definition.query.format,
                mime_type="text/csv",
                sha256="a" * 64,
                size_bytes=source.stat().st_size,
                storage_path=str(source),
                row_count=1,
                fields=dataset.definition.fields,
                created_at=datetime.now(UTC),
            )
        ),
        file_query_service=FileDatasetQueryService(
            compiler=FileQueryCompiler(), executor=DuckDBExecutor(Settings(data_dir=tmp_path))
        ),
    )
    request = ScreenDocumentQueryRequest(
        component_id="line-1",
        document=screen_document(
            data_binding={
                "chart_spec": chart_spec()
                .model_copy(update={"dataset_id": dataset.id})
                .model_dump(mode="json")
            }
        ),
    )
    return runtime, request


async def test_fifty_runtime_queries_use_one_real_parser_and_real_duckdb(tmp_path, monkeypatch):
    runtime, request = file_runtime(tmp_path)
    launches = []
    original = asyncio.create_subprocess_exec

    async def capture(*args, **kwargs):
        process = await original(*args, **kwargs)
        launches.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", capture)
    results = await asyncio.gather(
        *(
            runtime.query_document_component(request, request_id=f"reader-{index}")
            for index in range(50)
        )
    )
    assert len(launches) == 1
    assert all(result.rows == (("2026-01", 10),) for result in results)
    assert {result.request_id for result in results} == {f"reader-{index}" for index in range(50)}


async def test_runtime_file_decode_failure_has_stable_public_error(tmp_path):
    runtime, request = file_runtime(tmp_path, invalid=True)
    with pytest.raises(DataPulseError) as failure:
        await runtime.query_document_component(request, request_id="invalid-file")
    assert (failure.value.code, failure.value.status_code) == ("FILE_PARSE_INVALID", 422)


async def test_runtime_unrelated_processor_saturation_returns_429_and_reaps_workers(
    tmp_path, monkeypatch
):
    from datapulse.operations import processing

    runtime, request = file_runtime(tmp_path)
    ready = asyncio.Event()
    processes = []
    original = asyncio.create_subprocess_exec
    slots = tmp_path / "processor-slots"

    async def isolated_processor(*args, **kwargs):
        return await run_processor(*args, **kwargs, slot_directory=slots)

    monkeypatch.setattr(processing, "run_processor", isolated_processor)

    async def capture(*args, **kwargs):
        process = await original(*args, **kwargs)
        processes.append(process)
        if len(processes) == 2:
            ready.set()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", capture)
    occupied = [
        asyncio.create_task(
                isolated_processor(
                    [sys.executable, "-c", "import time; time.sleep(60)"], directory=tmp_path
                )
        )
        for _ in range(2)
    ]
    try:
        await asyncio.wait_for(ready.wait(), timeout=10)
        with pytest.raises(DataPulseError) as failure:
            await runtime.query_document_component(request, request_id="busy-file")
        assert (failure.value.code, failure.value.status_code) == ("FILE_PROCESSING_BUSY", 429)
    finally:
        for task in occupied:
            task.cancel()
        await asyncio.gather(*occupied, return_exceptions=True)
    assert all(process.returncode is not None for process in processes)
