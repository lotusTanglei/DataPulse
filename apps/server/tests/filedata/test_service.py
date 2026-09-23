import asyncio
import io

import pytest
from starlette.datastructures import Headers, UploadFile

from datapulse.filedata.repository import FileAssetRepository
from datapulse.filedata.service import FileAssetService
from datapulse.filedata.storage import FileStorage
from datapulse.metadata import create_metadata_engine, create_session_factory
from datapulse.settings import Settings
from tests.support.app import migrate_database

pytestmark = pytest.mark.anyio


async def test_cancelled_ingestion_reaps_parser_and_removes_unpublished_file(tmp_path, monkeypatch):
    migrate_database(tmp_path / "datapulse.db")
    settings = Settings(data_dir=tmp_path)
    engine = create_metadata_engine(settings)
    repository = FileAssetRepository(create_session_factory(engine))
    storage = FileStorage(settings, id_factory=lambda: "cancelled-upload")
    service = FileAssetService(repository=repository, storage=storage)
    started = asyncio.Event()
    original = asyncio.create_subprocess_exec

    async def capture(*args, **kwargs):
        process = await original(*args, **kwargs)
        started.set()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", capture)
    upload = UploadFile(
        io.BytesIO(b"region,amount\nEast,12\n"),
        filename="sales.csv",
        headers=Headers({"content-type": "text/csv"}),
    )
    ingestion = asyncio.create_task(service.ingest(upload, request_id="cancel-test"))
    try:
        await asyncio.wait_for(started.wait(), timeout=3)
        ingestion.cancel()
        with pytest.raises(asyncio.CancelledError):
            await ingestion
        assert await repository.list() == ()
        assert not (settings.resolved_files_dir() / "cancelled-upload").exists()
    finally:
        ingestion.cancel()
        await asyncio.gather(ingestion, return_exceptions=True)
        await engine.dispose()


async def test_delete_waits_for_preview_in_another_service_without_removing_parser_workspace(
    tmp_path, monkeypatch
):
    migrate_database(tmp_path / "datapulse.db")
    settings = Settings(data_dir=tmp_path)
    engine = create_metadata_engine(settings)
    other_engine = create_metadata_engine(settings)
    repository = FileAssetRepository(create_session_factory(engine))
    storage = FileStorage(settings, id_factory=lambda: "preview-delete")
    service = FileAssetService(repository=repository, storage=storage)
    other = FileAssetService(
        repository=FileAssetRepository(create_session_factory(other_engine)),
        storage=FileStorage(settings),
    )
    upload = UploadFile(
        io.BytesIO(b"region,amount\nEast,12\n"),
        filename="sales.csv",
        headers=Headers({"content-type": "text/csv"}),
    )
    asset = await service.ingest(upload, request_id="setup")
    started = asyncio.Event()
    release = asyncio.Event()
    original = asyncio.create_subprocess_exec

    async def capture(*args, **kwargs):
        process = await original(*args, **kwargs)
        started.set()
        await release.wait()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", capture)
    preview = asyncio.create_task(service.preview(asset.id, sheet_name=None, request_id="preview"))
    deletion = None
    try:
        await asyncio.wait_for(started.wait(), timeout=3)
        deletion = asyncio.create_task(other.delete(asset.id))
        await asyncio.sleep(0.1)
        assert not deletion.done(), "Deletion must wait until the preview releases its source"
        release.set()
        result = await asyncio.wait_for(preview, timeout=5)
        await asyncio.wait_for(deletion, timeout=5)
        assert result.result.rows == (("East", 12),)
        assert await repository.list() == ()
        assert not (settings.resolved_files_dir() / asset.id).exists()
    finally:
        release.set()
        pending = [preview] + ([deletion] if deletion is not None else [])
        await asyncio.gather(*pending, return_exceptions=True)
        await engine.dispose()
        await other_engine.dispose()
