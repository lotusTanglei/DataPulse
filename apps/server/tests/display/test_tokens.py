from datetime import UTC, datetime, timedelta

import pytest

from datapulse.display.tokens import (
    DisplaySessionCodec,
    DisplaySessionExpired,
    DisplaySessionInvalid,
)


def test_display_session_binds_screen_key_version_and_expiry() -> None:
    now = datetime(2026, 7, 30, 8, 0, tzinfo=UTC)
    codec = DisplaySessionCodec(
        signing_key=b"s" * 32,
        now=lambda: now,
    )

    token = codec.issue(
        screen_id="screen-1",
        key_version=3,
        lifetime=timedelta(days=30),
    )
    claims = codec.verify(token)

    assert claims.screen_id == "screen-1"
    assert claims.key_version == 3
    assert claims.issued_at == now
    assert claims.expires_at == now + timedelta(days=30)


def test_display_session_rejects_tampering_and_expiry() -> None:
    current = datetime(2026, 7, 30, 8, 0, tzinfo=UTC)
    codec = DisplaySessionCodec(
        signing_key=b"s" * 32,
        now=lambda: current,
    )
    token = codec.issue(
        screen_id="screen-1",
        key_version=1,
        lifetime=timedelta(minutes=5),
    )

    with pytest.raises(DisplaySessionInvalid):
        codec.verify(f"{token[:-1]}x")

    current += timedelta(minutes=6)
    with pytest.raises(DisplaySessionExpired):
        codec.verify(token)
