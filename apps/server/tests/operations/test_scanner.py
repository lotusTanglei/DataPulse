import asyncio
import io
import os
import signal
import sys

import pytest
from starlette.datastructures import Headers, UploadFile

from datapulse.errors import DataPulseError
from datapulse.filedata.storage import FileStorage
from datapulse.operations.scanner import CommandScanner
from datapulse.settings import Settings
from tests.support.app import build_test_app

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("cancellations", [1, 2])
async def test_scanner_cancellation_during_launch_reaps_child_before_releasing_slot(
    tmp_path, monkeypatch, cancellations
):
    scanner = CommandScanner(
        command=[sys.executable, "-c", "import time; time.sleep(60)"],
        temporary_dir=tmp_path,
        concurrency=1,
    )
    started = asyncio.Event()
    release = asyncio.Event()
    processes = []
    original = asyncio.create_subprocess_exec

    async def delayed_launch(*args, **kwargs):
        process = await original(*args, **kwargs)
        processes.append(process)
        started.set()
        await release.wait()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", delayed_launch)
    scan = asyncio.create_task(scanner(b"fixture", "text/plain", "fixture.txt"))
    try:
        await asyncio.wait_for(started.wait(), timeout=3)
        for _ in range(cancellations):
            scan.cancel()
            await asyncio.sleep(0.01)
        assert not scan.done(), "Scanner returned before its launched child could be reaped"
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(scan, timeout=3)
        assert processes[0].returncode is not None, "Cancelled scanner left its child running"
        with pytest.raises(ProcessLookupError):
            os.kill(processes[0].pid, 0)
        assert not list(tmp_path.glob("scan-*"))
        scanner.command = [sys.executable, "-c", "pass"]
        assert await scanner(b"clean", "text/plain", "next.txt") is True
    finally:
        release.set()
        scan.cancel()
        await asyncio.gather(scan, return_exceptions=True)
        for process in processes:
            if process.returncode is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await process.wait()


async def test_real_subprocess_exit_status_rejects_infected_data_before_storage(tmp_path):
    program = tmp_path / "scanner.py"
    program.write_text(
        "import pathlib,sys\n"
        "sys.exit(1 if b'infected' in pathlib.Path(sys.argv[1]).read_bytes() else 0)\n"
    )
    scanner = CommandScanner(
        command=[sys.executable, str(program)], temporary_dir=tmp_path / "quarantine"
    )
    storage = FileStorage(Settings(data_dir=tmp_path), scanner=scanner)
    file = UploadFile(
        filename="fixture.csv",
        file=io.BytesIO(b"value\ninfected\n"),
        headers=Headers({"content-type": "text/csv"}),
    )
    with pytest.raises(DataPulseError) as rejected:
        await storage.save(file)
    assert rejected.value.code == "UPLOAD_SCAN_REJECTED"
    assert not list((tmp_path / "files").glob("*/source.*"))
    clean = UploadFile(
        filename="fixture.csv",
        file=io.BytesIO(b"value\n1\n"),
        headers=Headers({"content-type": "text/csv"}),
    )
    stored = await storage.save(clean)
    assert stored.size_bytes == 8


async def test_scanner_failure_and_timeout_fail_closed_and_cleanup(tmp_path):
    for program, timeout in [("import sys;sys.exit(2)", 5), ("import time;time.sleep(10)", 0.1)]:
        scanner = CommandScanner(
            command=[sys.executable, "-c", program], temporary_dir=tmp_path, timeout_seconds=timeout
        )
        with pytest.raises(DataPulseError) as failed:
            await scanner(b"private-fixture", "text/plain", "ignore-original-name")
        assert failed.value.code == "UPLOAD_SCAN_UNAVAILABLE"
        assert not list(tmp_path.glob("scan-*"))


async def test_scanner_does_not_pass_application_secrets_to_child(tmp_path, monkeypatch):
    monkeypatch.setenv("DATAPULSE_MASTER_KEY", "must-not-reach-child")
    scanner = CommandScanner(
        command=[
            sys.executable,
            "-c",
            "import os,sys;sys.exit(2 if 'DATAPULSE_MASTER_KEY' in os.environ else 0)",
        ],
        temporary_dir=tmp_path,
    )
    assert await scanner(b"fixture", "text/plain", "name") is True


def test_configured_scanner_rejects_file_and_media_api_uploads(tmp_path, monkeypatch):
    import json

    monkeypatch.setenv(
        "DATAPULSE_UPLOAD_SCANNER_COMMAND",
        json.dumps([sys.executable, "-c", "import sys;sys.exit(1)"]),
    )
    with build_test_app(tmp_path) as app:
        client = app.client
        client.post(
            "/api/auth/setup",
            json={"code": app.setup_code, "username": "admin", "password": "fixture-password"},
            headers={"Origin": app.origin},
        )
        headers = {"Origin": app.origin, "X-CSRF-Token": client.cookies["datapulse_csrf"]}
        for endpoint, name, mime, content in [
            ("/api/admin/files", "fixture.csv", "text/csv", b"x\n1\n"),
            ("/api/admin/assets", "fixture.png", "image/png", b"untrusted-image"),
        ]:
            response = client.post(endpoint, files={"file": (name, content, mime)}, headers=headers)
            assert response.status_code == 422, response.text
            assert response.json()["error"]["code"] == "UPLOAD_SCAN_REJECTED"
        assert not list((tmp_path / "files").glob("*/source.*"))
