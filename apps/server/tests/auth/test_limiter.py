from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from datapulse.auth.limiter import LoginLimiter, LoginRateLimited


@dataclass
class MutableClock:
    current: datetime

    def __call__(self) -> datetime:
        return self.current


def test_sixth_attempt_in_window_is_rate_limited() -> None:
    clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
    limiter = LoginLimiter(
        max_failures=5,
        window=timedelta(minutes=15),
        clock=clock,
    )

    for _ in range(5):
        limiter.check_allowed("127.0.0.1")
        limiter.record_failure("127.0.0.1")

    with pytest.raises(LoginRateLimited):
        limiter.check_allowed("127.0.0.1")


def test_success_clears_failures_and_addresses_are_normalized() -> None:
    clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
    limiter = LoginLimiter(
        max_failures=2,
        window=timedelta(minutes=15),
        clock=clock,
    )
    limiter.record_failure("2001:0db8:0:0:0:0:0:1")
    limiter.record_failure("2001:db8::1")

    with pytest.raises(LoginRateLimited):
        limiter.check_allowed("2001:db8::1")

    limiter.record_success("2001:db8::1")
    limiter.check_allowed("2001:0db8:0:0:0:0:0:1")


def test_failure_window_expires() -> None:
    clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
    limiter = LoginLimiter(
        max_failures=1,
        window=timedelta(minutes=15),
        clock=clock,
    )
    limiter.record_failure("127.0.0.1")
    with pytest.raises(LoginRateLimited):
        limiter.check_allowed("127.0.0.1")

    clock.current += timedelta(minutes=15, seconds=1)

    limiter.check_allowed("127.0.0.1")
