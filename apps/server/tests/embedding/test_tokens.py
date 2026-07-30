import base64
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from datapulse.embedding.tokens import (
    EmbedTicketCodec,
    EmbedTicketExpired,
    EmbedTicketInvalid,
    EmbedTicketLifetimeInvalid,
    EmbedTicketOriginInvalid,
    validate_embed_origin,
)
from datapulse.settings import Settings


def test_ticket_binds_screen_origin_parameters_and_expiry() -> None:
    now = datetime(2026, 7, 30, 8, 0, tzinfo=UTC)
    codec = EmbedTicketCodec(signing_key=b"e" * 32, now=lambda: now)

    ticket = codec.issue(
        screen_id="screen-1",
        allowed_origin="https://host.example.com",
        parameters={"region": "east"},
        mutable_parameters=("region",),
        lifetime=timedelta(hours=1),
    )
    claims = codec.verify(ticket, expected_screen_id="screen-1")

    assert claims.screen_id == "screen-1"
    assert claims.allowed_origin == "https://host.example.com"
    assert claims.parameters == {"region": "east"}
    assert claims.mutable_parameters == ("region",)
    assert claims.issued_at == now
    assert claims.expires_at == now + timedelta(hours=1)


@pytest.mark.parametrize(
    "origin",
    [
        "http://host.example.com",
        "https://host.example.com/path",
        "https://host.example.com/?query=1",
        "https://user@host.example.com",
        "javascript:alert(1)",
    ],
)
def test_embed_origin_rejects_unsafe_or_path_bearing_values(origin: str) -> None:
    with pytest.raises(EmbedTicketOriginInvalid):
        validate_embed_origin(origin)


@pytest.mark.parametrize(
    "origin",
    [
        "https://host.example.com",
        "https://host.example.com:8443",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://[::1]:3000",
    ],
)
def test_embed_origin_accepts_https_and_local_development(origin: str) -> None:
    assert validate_embed_origin(origin) == origin


def test_ticket_rejects_wrong_screen_audience_expiry_and_excess_lifetime() -> None:
    current = datetime(2026, 7, 30, 8, 0, tzinfo=UTC)
    codec = EmbedTicketCodec(signing_key=b"e" * 32, now=lambda: current)
    ticket = codec.issue(
        screen_id="screen-1",
        allowed_origin="https://host.example.com",
        parameters={},
        mutable_parameters=(),
        lifetime=timedelta(minutes=5),
    )

    with pytest.raises(EmbedTicketInvalid):
        codec.verify(ticket, expected_screen_id="screen-2")

    payload = jwt.decode(
        ticket,
        b"e" * 32,
        algorithms=["HS256"],
        audience="datapulse-embed",
        options={"verify_exp": False},
    )
    payload["aud"] = "wrong-audience"
    wrong_audience = jwt.encode(payload, b"e" * 32, algorithm="HS256")
    with pytest.raises(EmbedTicketInvalid):
        codec.verify(wrong_audience, expected_screen_id="screen-1")

    current += timedelta(minutes=6)
    with pytest.raises(EmbedTicketExpired):
        codec.verify(ticket, expected_screen_id="screen-1")

    with pytest.raises(EmbedTicketLifetimeInvalid):
        codec.issue(
            screen_id="screen-1",
            allowed_origin="https://host.example.com",
            parameters={},
            mutable_parameters=(),
            lifetime=timedelta(hours=8, seconds=1),
        )


@pytest.mark.parametrize(
    "encoded",
    [
        "not-base64",
        base64.urlsafe_b64encode(b"short").decode(),
        base64.urlsafe_b64encode(b"x" * 33).decode(),
    ],
)
def test_settings_rejects_malformed_signing_keys(encoded: str) -> None:
    with pytest.raises(ValueError, match="DATAPULSE_SIGNING_KEY"):
        Settings(signing_key=encoded).signing_key_bytes()
