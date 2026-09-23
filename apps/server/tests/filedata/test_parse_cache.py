import asyncio
import gc
import os
import signal
import weakref

import pytest

from datapulse.contracts.dataset import FileFormat
from datapulse.filedata import parsers

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def isolated_processor_slots(tmp_path, monkeypatch):
    from datapulse.operations import processing

    original = processing.run_processor

    async def run(*args, **kwargs):
        return await original(*args, **kwargs, slot_directory=tmp_path / "processor-slots")

    monkeypatch.setattr(processing, "run_processor", run)


async def test_repeated_reader_cancellation_waits_for_launch_and_reaps_shared_child(
    tmp_path, monkeypatch
):
    source = tmp_path / "source.csv"
    source.write_text("amount\n12\n")
    started, release = asyncio.Event(), asyncio.Event()
    processes = []
    original = asyncio.create_subprocess_exec

    async def delayed(*args, **kwargs):
        process = await original(*args, **kwargs)
        processes.append(process)
        started.set()
        await release.wait()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", delayed)
    reader = asyncio.create_task(
        parsers.parse_file(source, FileFormat.CSV, sheet_name=None, max_rows=10)
    )
    try:
        await asyncio.wait_for(started.wait(), timeout=10)
        reader.cancel()
        await asyncio.sleep(0.01)
        reader.cancel()
        await asyncio.sleep(0.01)
        assert not reader.done(), "Reader returned before its launched child could be reaped"
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await reader
        assert processes[0].returncode is not None
        with pytest.raises(ProcessLookupError):
            os.kill(processes[0].pid, 0)
        assert not list(tmp_path.glob(".parse-*"))
        monkeypatch.setattr(asyncio, "create_subprocess_exec", original)
        assert (
            await parsers.parse_file(source, FileFormat.CSV, sheet_name=None, max_rows=10)
        ).sample_rows == ({"amount": 12},)
    finally:
        release.set()
        reader.cancel()
        await asyncio.gather(reader, return_exceptions=True)
        for process in processes:
            if process.returncode is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await process.communicate()


async def test_fifty_concurrent_reads_share_one_real_parser_and_cache_is_not_mutable(
    tmp_path, monkeypatch
):
    source = tmp_path / "source.csv"
    source.write_text("amount\n12\n")
    launches = []
    original = asyncio.create_subprocess_exec

    async def capture(*args, **kwargs):
        process = await original(*args, **kwargs)
        launches.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", capture)
    results = await asyncio.gather(
        *(
            parsers.parse_file(source, FileFormat.CSV, sheet_name=None, max_rows=10)
            for _ in range(50)
        ),
        return_exceptions=True,
    )
    assert not [result for result in results if isinstance(result, BaseException)]
    assert len(launches) == 1
    assert all(result.sample_rows == ({"amount": 12},) for result in results)
    results[0].sample_rows[0]["amount"] = "changed"
    assert results[1].sample_rows == ({"amount": 12},)
    cached = await parsers.parse_file(source, FileFormat.CSV, sheet_name=None, max_rows=10)
    assert cached.sample_rows == ({"amount": 12},)
    assert len(launches) == 1


async def test_cache_revalidates_replaced_source_and_missing_or_changed_normalized_file(tmp_path):
    source = tmp_path / "source.json"
    source.write_text('[{"amount":12}]')
    first = await parsers.parse_file(source, FileFormat.JSON, sheet_name=None, max_rows=10)
    first.normalized_path.unlink()
    regenerated = await parsers.parse_file(source, FileFormat.JSON, sheet_name=None, max_rows=10)
    assert regenerated.normalized_path.is_file()
    regenerated.normalized_path.write_bytes(b"invalid parquet")
    repaired = await parsers.parse_file(source, FileFormat.JSON, sheet_name=None, max_rows=10)
    assert repaired.normalized_path.read_bytes().startswith(b"PAR1")
    previous = source.stat()
    replacement = tmp_path / "replacement.json"
    replacement.write_text('[{"amount":99}]')
    os.utime(replacement, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    replacement.replace(source)
    changed = await parsers.parse_file(source, FileFormat.JSON, sheet_name=None, max_rows=10)
    assert changed.sample_rows == ({"amount": 99},)
    source.unlink()
    with pytest.raises(parsers.FileParseInvalid):
        await parsers.parse_file(source, FileFormat.JSON, sheet_name=None, max_rows=10)


async def test_cancelling_one_waiter_keeps_shared_parser_alive_for_other_reader(
    tmp_path, monkeypatch
):
    source = tmp_path / "source.csv"
    source.write_text("amount\n12\n")
    started, release = asyncio.Event(), asyncio.Event()
    processes = []
    original = asyncio.create_subprocess_exec

    async def delayed(*args, **kwargs):
        process = await original(*args, **kwargs)
        processes.append(process)
        started.set()
        await release.wait()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", delayed)
    first = asyncio.create_task(
        parsers.parse_file(source, FileFormat.CSV, sheet_name=None, max_rows=10)
    )
    second = asyncio.create_task(
        parsers.parse_file(source, FileFormat.CSV, sheet_name=None, max_rows=10)
    )
    try:
        await asyncio.wait_for(started.wait(), timeout=10)
        first.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await first
        result = await second
        assert result.sample_rows == ({"amount": 12},)
        assert len(processes) == 1
    finally:
        release.set()
        for task in (first, second):
            task.cancel()
        await asyncio.gather(first, second, return_exceptions=True)


async def test_source_changed_during_parse_is_rejected_and_next_read_is_fresh(
    tmp_path, monkeypatch
):
    source = tmp_path / "source.csv"
    source.write_text("amount\n12\n")
    original = parsers.run_json_worker

    async def changed(*args, **kwargs):
        result = await original(*args, **kwargs)
        source.write_text("amount\n99\n")
        return result

    monkeypatch.setattr(parsers, "run_json_worker", changed)
    with pytest.raises(parsers.FileParseInvalid, match="changed"):
        await parsers.parse_file(source, FileFormat.CSV, sheet_name=None, max_rows=10)
    monkeypatch.setattr(parsers, "run_json_worker", original)
    result = await parsers.parse_file(source, FileFormat.CSV, sheet_name=None, max_rows=10)
    assert result.sample_rows == ({"amount": 99},)


@pytest.mark.parametrize("bound", ["entries", "bytes"])
async def test_parse_cache_evicts_at_its_memory_and_entry_bounds(tmp_path, monkeypatch, bound):
    first, second = tmp_path / "first.csv", tmp_path / "second.csv"
    first.write_text("amount\n12\n")
    second.write_text("amount\n34\n")
    launches = []
    original = asyncio.create_subprocess_exec

    async def capture(*args, **kwargs):
        process = await original(*args, **kwargs)
        launches.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", capture)
    if bound == "entries":
        monkeypatch.setattr(parsers, "_CACHE_MAX_ENTRIES", 1)
    else:
        monkeypatch.setattr(parsers, "_CACHE_MAX_BYTES", 1)
    for source in (first, second, first):
        await parsers.parse_file(source, FileFormat.CSV, sheet_name=None, max_rows=10)
    assert len(launches) == 3


def test_completed_cache_does_not_retain_a_closed_event_loop(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("amount\n12\n")
    loop = asyncio.new_event_loop()
    reference = weakref.ref(loop)
    try:
        loop.run_until_complete(
            parsers.parse_file(source, FileFormat.CSV, sheet_name=None, max_rows=10)
        )
    finally:
        loop.close()
    del loop
    gc.collect()
    assert reference() is None
