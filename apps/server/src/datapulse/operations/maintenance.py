"""Cooperative process leases shared by the API, workers and offline backup."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class MaintenanceBusy(RuntimeError):
    """A running instance or maintenance operation holds a conflicting lease."""


@contextmanager
def _lease(data_dir: Path, *, exclusive: bool) -> Iterator[None]:
    # The supported deployment platforms are Linux and macOS. Do not silently
    # degrade to an in-process lock on other platforms.
    import fcntl

    data_dir.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        data_dir / ".maintenance.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
    )
    try:
        try:
            fcntl.flock(descriptor, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise MaintenanceBusy(
                "A running instance or active maintenance operation holds a lease."
            ) from error
        yield
    finally:
        os.close(descriptor)


def runtime_lease(data_dir: Path):
    """Hold for the entire API/worker lifespan, including initialization."""
    return _lease(data_dir, exclusive=False)


def maintenance_lease(data_dir: Path):
    """Require all cooperating API and worker processes to be stopped."""
    return _lease(data_dir, exclusive=True)
