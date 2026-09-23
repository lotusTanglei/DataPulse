"""Short-lived, resource-limited processors with bounded pipes and shared slots."""

import asyncio
import json
import math
import os
import signal
import sys
import tempfile
from collections.abc import Awaitable
from pathlib import Path

from filelock import AsyncFileLock, Timeout

from datapulse.operations.process_runner import bounded_command, processor_environment


class ProcessorFailed(ValueError):
    pass


class ProcessorBusy(ProcessorFailed):
    pass


class ProcessorInputInvalid(ProcessorFailed):
    pass


async def complete_cleanup[T](awaitable: Awaitable[T]) -> T:
    """Join owned cleanup even if its caller receives more cancellation requests."""
    cleanup = asyncio.ensure_future(awaitable)
    while not cleanup.done():
        try:
            await asyncio.shield(cleanup)
        except asyncio.CancelledError:
            # Cancellation still propagates from the caller's original except
            # block after cleanup. Never forward subsequent cancels to a launch
            # or reap operation, which may already own a live child process.
            continue
    return cleanup.result()


async def _read_bounded(stream: asyncio.StreamReader, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while chunk := await stream.read(64 * 1024):
        size += len(chunk)
        if size > limit:
            raise ProcessorFailed("Processor output exceeds the size limit.")
        chunks.append(chunk)
    return b"".join(chunks)


async def _kill(process: asyncio.subprocess.Process) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass

    async def drain(stream):
        if stream is not None:
            while await stream.read(64 * 1024):
                pass

    # wait() alone can deadlock while a full PIPE transport is paused, even
    # after SIGKILL. Drain the bounded pending buffers before reaping.
    await asyncio.gather(drain(process.stdout), drain(process.stderr), process.wait())


async def run_processor(
    command: list[str],
    *,
    directory: Path,
    timeout_seconds: float = 30,
    memory_mb: int = 1024,
    max_output_bytes: int = 8 * 1024 * 1024,
    concurrency: int = 2,
    slot_directory: Path | None = None,
) -> bytes:
    slots = (
        slot_directory
        or Path(tempfile.gettempdir()).resolve() / f"datapulse-processors-{os.getuid()}"
    )
    if slots.is_symlink():
        raise ProcessorFailed("Processor slot directory must not be a symbolic link.")
    slots.mkdir(parents=True, exist_ok=True, mode=0o700)
    for number in range(concurrency):
        lock = AsyncFileLock(str(slots / f"slot-{number}.lock"), timeout=0, run_in_executor=False)
        try:
            await lock.acquire()
        except Timeout:
            continue
        try:
            return await _execute(command, directory, timeout_seconds, memory_mb, max_output_bytes)
        finally:
            await lock.release()
    raise ProcessorBusy("File processing is busy. Retry shortly.")


async def _execute(
    command: list[str], directory: Path, timeout: float, memory: int, limit: int
) -> bytes:
    launch = asyncio.create_task(
        asyncio.create_subprocess_exec(
            *bounded_command(command, cpu_seconds=max(1, math.ceil(timeout)), memory_mb=memory),
            cwd=directory,
            env=processor_environment(),
            start_new_session=True,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    )
    try:
        process = await asyncio.shield(launch)
    except asyncio.CancelledError:
        process = await complete_cleanup(launch)
        await complete_cleanup(_kill(process))
        raise
    except OSError as error:
        raise ProcessorFailed("The processor is unavailable.") from error
    tasks = [
        asyncio.create_task(_read_bounded(process.stdout, limit)),
        asyncio.create_task(_read_bounded(process.stderr, limit)),
        asyncio.create_task(process.wait()),
    ]
    try:
        output, _diagnostics, code = await asyncio.wait_for(asyncio.gather(*tasks), timeout)
        if code != 0:
            raise ProcessorFailed("The processor failed or exceeded a resource limit.")
        return output
    except (TimeoutError, asyncio.CancelledError, ProcessorFailed) as error:
        for task in tasks:
            task.cancel()
        await complete_cleanup(asyncio.gather(*tasks, return_exceptions=True))
        await complete_cleanup(_kill(process))
        if isinstance(error, TimeoutError):
            raise ProcessorFailed("The processor timed out.") from error
        raise


async def run_json_worker(request: dict, *, directory: Path, timeout_seconds: float = 30) -> dict:
    descriptor, filename = tempfile.mkstemp(prefix="request-", suffix=".json", dir=directory)
    request_path = Path(filename)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(request, stream)
    try:
        output = await run_processor(
            [sys.executable, "-m", "datapulse.operations.parse_worker", str(request_path)],
            directory=directory,
            timeout_seconds=timeout_seconds,
        )
    finally:
        request_path.unlink(missing_ok=True)
    try:
        result = json.loads(output)
        if not isinstance(result, dict):
            raise ProcessorFailed("The processor returned invalid output.")
        if result.get("ok") is not True:
            messages = {"IMAGE_PIXEL_LIMIT": "The image exceeds the pixel limit."}
            raise ProcessorInputInvalid(
                messages.get(result.get("error_code"), "The input cannot be decoded safely.")
            )
        return result
    except (ValueError, TypeError) as error:
        if isinstance(error, ProcessorFailed):
            raise
        raise ProcessorFailed("The processor returned invalid output.") from error
