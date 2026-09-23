"""Configured local antivirus adapter. Exit 0 is clean, 1 infected, others fail closed."""

import asyncio
import os
import signal
import tempfile
from pathlib import Path

from filelock import AsyncFileLock, Timeout

from datapulse.errors import DataPulseError
from datapulse.operations.process_runner import bounded_command, processor_environment
from datapulse.operations.processing import complete_cleanup


class CommandScanner:
    def __init__(
        self,
        *,
        command: list[str] | tuple[str, ...],
        temporary_dir: Path,
        timeout_seconds: float = 30,
        memory_mb: int = 1024,
        concurrency: int = 2,
    ):
        if not command or any(
            not isinstance(arg, str) or not arg or "\0" in arg for arg in command
        ):
            raise ValueError("The scanner command must contain nonempty arguments.")
        self.command = list(command)
        self.temporary_dir = temporary_dir
        self.timeout_seconds = timeout_seconds
        self.memory_mb = memory_mb
        self.concurrency = concurrency

    async def scan_path(self, path: Path) -> None:
        self.temporary_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        for slot in range(self.concurrency):
            lock = AsyncFileLock(str(self.temporary_dir / f".scanner-{slot}.lock"), timeout=0)
            try:
                await lock.acquire()
            except Timeout:
                continue
            try:
                await self._run(path)
                return
            finally:
                await lock.release()
        raise DataPulseError("UPLOAD_SCAN_BUSY", "File scanning is busy. Retry shortly.", 429)

    async def _run(self, path: Path) -> None:
        launch = asyncio.create_task(
            asyncio.create_subprocess_exec(
                *bounded_command(
                    [*self.command, str(path.resolve())],
                    cpu_seconds=max(1, int(self.timeout_seconds) + 1),
                    memory_mb=self.memory_mb,
                ),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                start_new_session=True,
                env=processor_environment(),
            )
        )
        try:
            process = await asyncio.shield(launch)
        except asyncio.CancelledError:
            # Creation may already have forked the child. Wait for its handle
            # before removing quarantine input or releasing the scanner slot.
            process = await complete_cleanup(launch)
            await complete_cleanup(self._kill(process))
            raise
        except OSError as error:
            raise DataPulseError(
                "UPLOAD_SCAN_UNAVAILABLE", "File scanning is unavailable.", 503
            ) from error
        try:
            code = await asyncio.wait_for(process.wait(), timeout=self.timeout_seconds)
        except (TimeoutError, asyncio.CancelledError) as error:
            await complete_cleanup(self._kill(process))
            if isinstance(error, asyncio.CancelledError):
                raise
            raise DataPulseError(
                "UPLOAD_SCAN_UNAVAILABLE", "File scanning timed out.", 503
            ) from error
        if code == 1:
            raise DataPulseError(
                "UPLOAD_SCAN_REJECTED", "The upload was rejected by the scanner.", 422
            )
        if code != 0:
            raise DataPulseError("UPLOAD_SCAN_UNAVAILABLE", "File scanning is unavailable.", 503)

    @staticmethod
    async def _kill(process: asyncio.subprocess.Process) -> None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        await process.wait()

    async def __call__(self, content: bytes, mime_type: str, original_name: str) -> bool:
        del mime_type, original_name
        self.temporary_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, raw_path = tempfile.mkstemp(prefix="scan-", dir=self.temporary_dir)
        path = Path(raw_path)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
            await self.scan_path(path)
            return True
        finally:
            path.unlink(missing_ok=True)
