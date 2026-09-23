import asyncio
import json
import os
import signal
import sys

import pytest

from datapulse.contracts.dataset import FileFormat
from datapulse.filedata import parsers
from datapulse.screen.media import MediaInspector, MediaLimits
from tests.support.media import image_bytes

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("phase", ["launch", "cleanup"])
async def test_repeated_processor_cancellation_cannot_interrupt_reaping(
    tmp_path, monkeypatch, phase
):
    from datapulse.operations import processing

    started, cleanup_started, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    processes = []
    original = asyncio.create_subprocess_exec
    original_kill = processing._kill

    async def delayed_launch(*args, **kwargs):
        process = await original(*args, **kwargs)
        processes.append(process)
        started.set()
        if phase == "launch":
            await release.wait()
        return process

    async def delayed_kill(process):
        cleanup_started.set()
        if phase == "cleanup":
            await release.wait()
        await original_kill(process)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", delayed_launch)
    monkeypatch.setattr(processing, "_kill", delayed_kill)
    slots = tmp_path / "slots"
    worker = asyncio.create_task(
        processing.run_processor(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            directory=tmp_path,
            slot_directory=slots,
            concurrency=1,
        )
    )
    try:
        await asyncio.wait_for(started.wait(), timeout=10)
        worker.cancel()
        if phase == "cleanup":
            await asyncio.wait_for(cleanup_started.wait(), timeout=10)
        else:
            await asyncio.sleep(0.01)
        worker.cancel()
        await asyncio.sleep(0.01)
        assert not worker.done(), "Cancellation interrupted owned processor cleanup"
        with pytest.raises(processing.ProcessorBusy):
            await processing.run_processor(
                [sys.executable, "-c", "pass"],
                directory=tmp_path,
                slot_directory=slots,
                concurrency=1,
            )
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await worker
        assert processes[0].returncode is not None
        with pytest.raises(ProcessLookupError):
            os.kill(processes[0].pid, 0)
        assert (
            await processing.run_processor(
                [sys.executable, "-c", "print('clean')"],
                directory=tmp_path,
                slot_directory=slots,
                concurrency=1,
            )
            == b"clean\n"
        )
    finally:
        release.set()
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)
        for process in processes:
            if process.returncode is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await process.communicate()


async def test_file_and_image_decoding_do_not_run_in_the_api_process(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Untrusted bytes decoded in API process")

    monkeypatch.setattr(parsers, "_parse_sync", forbidden)
    monkeypatch.setattr(MediaInspector, "_image", forbidden)
    file = tmp_path / "sales.csv"
    file.write_text("region,amount\nEast,10\n")
    parsed = await parsers.parse_file(file, FileFormat.CSV, sheet_name=None, max_rows=10)
    assert parsed.row_count == 1
    result = await MediaInspector().inspect(image_bytes(), "image/png", ".png")
    assert result.metadata.validated


async def test_processor_scrubs_credentials_and_returns_bounded_output(tmp_path, monkeypatch):
    from datapulse.operations.processing import ProcessorFailed, run_processor

    monkeypatch.setenv("DATAPULSE_MASTER_KEY", "private-master")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "private-cloud")
    output = await run_processor(
        [sys.executable, "-c", "import json, os; print(json.dumps(dict(os.environ)))"],
        directory=tmp_path,
    )
    environment = json.loads(output)
    assert "DATAPULSE_MASTER_KEY" not in environment
    assert "AWS_SECRET_ACCESS_KEY" not in environment
    with pytest.raises(ProcessorFailed, match="output"):
        await asyncio.wait_for(
            run_processor(
                [
                    sys.executable,
                    "-c",
                    "import sys,time; sys.stdout.write('x' * 10000000); time.sleep(60)",
                ],
                directory=tmp_path,
                max_output_bytes=1000,
            ),
            timeout=3,
        )


async def test_processor_timeout_kills_and_reaps_child(tmp_path, monkeypatch):
    from datapulse.operations.processing import ProcessorFailed, run_processor

    processes = []
    original = asyncio.create_subprocess_exec

    async def capture(*args, **kwargs):
        process = await original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", capture)
    with pytest.raises(ProcessorFailed, match="timed out"):
        await run_processor(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            directory=tmp_path,
            timeout_seconds=0.3,
        )
    assert processes[0].returncode is not None
    with pytest.raises(ProcessLookupError):
        os.kill(processes[0].pid, 0)


async def test_processor_cancellation_releases_shared_slot_and_reaps_child(tmp_path):
    from datapulse.operations.processing import ProcessorBusy, run_processor

    slots = tmp_path / "slots"
    script = (
        "import os,time; from pathlib import Path; "
        "Path('pid').write_text(str(os.getpid())); time.sleep(60)"
    )
    task = asyncio.create_task(
        run_processor(
            [sys.executable, "-c", script], directory=tmp_path, slot_directory=slots, concurrency=1
        )
    )
    try:
        async with asyncio.timeout(3):
            while not (tmp_path / "pid").exists():
                await asyncio.sleep(0.01)
        with pytest.raises(ProcessorBusy):
            await run_processor(
                [sys.executable, "-c", "print('{}')"],
                directory=tmp_path,
                slot_directory=slots,
                concurrency=1,
            )
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    with pytest.raises(ProcessLookupError):
        os.kill(int((tmp_path / "pid").read_text()), 0)
    assert (
        await run_processor(
            [sys.executable, "-c", "print('{}')"],
            directory=tmp_path,
            slot_directory=slots,
            concurrency=1,
        )
        == b"{}\n"
    )


async def test_image_decode_timeout_releases_inspector_slot():
    from datapulse.screen.media import MediaUnavailable

    inspector = MediaInspector(MediaLimits(concurrency=1, timeout_seconds=0.00001))
    with pytest.raises(MediaUnavailable):
        await inspector.inspect(image_bytes(), "image/png", ".png")
    assert not inspector._slots.locked()


async def test_cancelled_file_parse_cleans_staging_and_preserves_source(tmp_path, monkeypatch):
    file = tmp_path / "request.json"
    file.write_text('[{"amount": 12}]')
    started = asyncio.Event()
    original = asyncio.create_subprocess_exec
    processes = []

    async def capture(*args, **kwargs):
        process = await original(*args, **kwargs)
        processes.append(process)
        started.set()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", capture)
    task = asyncio.create_task(
        parsers.parse_file(file, FileFormat.JSON, sheet_name=None, max_rows=10)
    )
    await asyncio.wait_for(started.wait(), timeout=3)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert processes[0].returncode is not None
    assert file.read_text() == '[{"amount": 12}]'
    assert not list(tmp_path.glob(".parse-*"))
    assert not (tmp_path / "request.normalized.parquet").exists()
    assert (
        await parsers.parse_file(file, FileFormat.JSON, sheet_name=None, max_rows=10)
    ).row_count == 1
