import asyncio
import hashlib
import io
import os
import sys
from pathlib import Path

import pytest

from datapulse.filedata.storage import (
    FileEmpty,
    FileNotFound,
    FileStorage,
    FileTooLarge,
    FileTypeUnsupported,
)
from datapulse.operations.scanner import CommandScanner
from datapulse.settings import Settings

pytestmark = pytest.mark.anyio


class InMemoryUpload:
    def __init__(self, *, filename: str, content_type: str, content: bytes) -> None:
        self.filename = filename
        self.content_type = content_type
        self.file = io.BytesIO(content)

    async def seek(self, offset: int) -> None:
        self.file.seek(offset)

    async def read(self, size: int = -1) -> bytes:
        return self.file.read(size)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        data_dir=tmp_path,
        file_max_bytes=32,
    )


def upload(*, filename: str, content_type: str, content: bytes) -> InMemoryUpload:
    return InMemoryUpload(filename=filename, content_type=content_type, content=content)


async def test_save_stores_file_inside_generated_asset_directory(
    settings: Settings,
) -> None:
    storage = FileStorage(settings, id_factory=lambda: "asset-1")
    stored = await storage.save(
        upload(
            filename="../../sales.csv",
            content_type="text/csv",
            content="name,amount\n华东,10\n".encode(),
        )
    )

    path = Path(stored.storage_path)

    assert stored.asset_id == "asset-1"
    assert stored.original_name == "../../sales.csv"
    assert stored.size_bytes > 0
    assert stored.sha256 == hashlib.sha256("name,amount\n华东,10\n".encode()).hexdigest()
    assert path.parent == settings.resolved_files_dir() / "asset-1"
    assert path.name == "source.csv"
    assert ".." not in path.parts
    assert path.read_bytes() == "name,amount\n华东,10\n".encode()


async def test_cancelled_real_scanner_reaps_child_and_removes_upload_staging(settings, tmp_path):
    marker = tmp_path / "scanner.pid"
    script = (
        "import os,time; from pathlib import Path; "
        f"Path({str(marker)!r}).write_text(str(os.getpid())); time.sleep(60)"
    )
    scanner = CommandScanner(
        command=[sys.executable, "-c", script], temporary_dir=tmp_path / "scanner", concurrency=1
    )
    storage = FileStorage(settings, id_factory=lambda: "cancelled-scan", scanner=scanner)
    saving = asyncio.create_task(
        storage.save(upload(filename="sales.csv", content_type="text/csv", content=b"amount\n12\n"))
    )
    try:
        async with asyncio.timeout(3):
            while not marker.exists():
                await asyncio.sleep(0.01)
        saving.cancel()
        with pytest.raises(asyncio.CancelledError):
            await saving
        assert not (settings.resolved_files_dir() / "cancelled-scan").exists()
        with pytest.raises(ProcessLookupError):
            os.kill(int(marker.read_text()), 0)
    finally:
        saving.cancel()
        await asyncio.gather(saving, return_exceptions=True)


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("sales.txt", "text/plain"),
        ("sales.csv", "application/json"),
        ("sales.parquet", "text/csv"),
    ],
)
async def test_save_rejects_unknown_mime_and_extension_mismatch(
    settings: Settings,
    filename: str,
    content_type: str,
) -> None:
    storage = FileStorage(settings, id_factory=lambda: "asset-1")

    with pytest.raises(FileTypeUnsupported) as captured:
        await storage.save(
            upload(
                filename=filename,
                content_type=content_type,
                content=b"col\n1\n",
            )
        )

    assert captured.value.code == "FILE_TYPE_UNSUPPORTED"


async def test_save_rejects_empty_file(settings: Settings) -> None:
    storage = FileStorage(settings, id_factory=lambda: "asset-1")

    with pytest.raises(FileEmpty) as captured:
        await storage.save(
            upload(
                filename="sales.csv",
                content_type="text/csv",
                content=b"",
            )
        )

    assert captured.value.code == "FILE_EMPTY"


async def test_save_rejects_oversized_file(settings: Settings) -> None:
    storage = FileStorage(settings, id_factory=lambda: "asset-1")

    with pytest.raises(FileTooLarge) as captured:
        await storage.save(
            upload(
                filename="sales.csv",
                content_type="text/csv",
                content=b"x" * 33,
            )
        )

    assert captured.value.code == "FILE_TOO_LARGE"


async def test_save_allows_duplicate_hash_with_distinct_asset_paths(settings: Settings) -> None:
    asset_ids = iter(("asset-1", "asset-2"))
    storage = FileStorage(settings, id_factory=lambda: next(asset_ids))
    content = b"region,amount\nnorth,10\n"

    first = await storage.save(
        upload(filename="sales.csv", content_type="text/csv", content=content)
    )
    second = await storage.save(
        upload(filename="sales.csv", content_type="text/csv", content=content)
    )

    assert first.sha256 == second.sha256
    assert first.storage_path != second.storage_path
    assert Path(first.storage_path).is_file()
    assert Path(second.storage_path).is_file()


async def test_open_read_rejects_soft_links_and_missing_files(settings: Settings) -> None:
    storage = FileStorage(settings, id_factory=lambda: "asset-1")
    stored = await storage.save(
        upload(
            filename="sales.csv",
            content_type="text/csv",
            content=b"region,amount\nnorth,10\n",
        )
    )

    stored_path = Path(stored.storage_path)
    outside = settings.data_dir / "outside.csv"
    outside.write_bytes(b"leak")
    stored_path.unlink()
    stored_path.symlink_to(outside)

    with pytest.raises(FileNotFound) as captured:
        with storage.open_read("asset-1"):
            pytest.fail("soft links must not be opened")

    assert captured.value.code == "FILE_NOT_FOUND"

    stored_path.unlink()
    with pytest.raises(FileNotFound):
        with storage.open_read("asset-1"):
            pytest.fail("missing files must not be opened")
