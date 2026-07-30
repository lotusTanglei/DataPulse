from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from ipaddress import ip_address


class LoginRateLimited(Exception):
    pass


@dataclass
class FailureWindow:
    started_at: datetime
    failures: int


class LoginLimiter:
    def __init__(
        self,
        *,
        max_failures: int,
        window: timedelta,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._max_failures = max_failures
        self._window = window
        self._clock = clock or (lambda: datetime.now(UTC))
        self._failures: dict[str, FailureWindow] = {}

    @staticmethod
    def _normalize(client_ip: str) -> str:
        try:
            return ip_address(client_ip).compressed
        except ValueError:
            return client_ip.strip().lower()

    def _active_window(self, client_ip: str) -> FailureWindow | None:
        key = self._normalize(client_ip)
        failure_window = self._failures.get(key)
        if failure_window is not None and self._clock() - failure_window.started_at > self._window:
            del self._failures[key]
            return None
        return failure_window

    def check_allowed(self, client_ip: str) -> None:
        failure_window = self._active_window(client_ip)
        if failure_window is not None and failure_window.failures >= self._max_failures:
            raise LoginRateLimited

    def record_failure(self, client_ip: str) -> None:
        key = self._normalize(client_ip)
        failure_window = self._active_window(client_ip)
        if failure_window is None:
            self._failures[key] = FailureWindow(started_at=self._clock(), failures=1)
        else:
            failure_window.failures += 1

    def record_success(self, client_ip: str) -> None:
        self._failures.pop(self._normalize(client_ip), None)
