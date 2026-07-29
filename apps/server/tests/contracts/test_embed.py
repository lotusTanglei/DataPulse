from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from datapulse.contracts.embed import EmbedMessageEnvelope, EmbedTicketClaims


def ticket_payload() -> dict[str, object]:
    issued_at = datetime(2026, 7, 29, 10, 0, tzinfo=UTC)
    return {
        "schema_version": 1,
        "issuer": "datapulse",
        "audience": "datapulse-embed",
        "dashboard_id": "executive-overview",
        "published_version_id": "version-7",
        "allowed_origin": "https://host.example.com",
        "issued_at": issued_at,
        "expires_at": issued_at + timedelta(minutes=5),
        "ai_enabled": True,
        "parameters": {"region": "east"},
    }


def test_embed_ticket_round_trips() -> None:
    ticket = EmbedTicketClaims.model_validate(ticket_payload())

    restored = EmbedTicketClaims.model_validate_json(ticket.model_dump_json())

    assert restored == ticket
    assert restored.allowed_origin == "https://host.example.com"


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "http://host.example.com",
        "https://host.example.com/path",
    ],
)
def test_embed_ticket_rejects_unsafe_origins(origin: str) -> None:
    payload = ticket_payload()
    payload["allowed_origin"] = origin

    with pytest.raises(ValidationError):
        EmbedTicketClaims.model_validate(payload)


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
def test_embed_ticket_allows_local_http_origins(origin: str) -> None:
    payload = ticket_payload()
    payload["allowed_origin"] = origin

    ticket = EmbedTicketClaims.model_validate(payload)

    assert ticket.allowed_origin == origin


def test_embed_ticket_requires_expiration_after_issue_time() -> None:
    payload = ticket_payload()
    payload["expires_at"] = payload["issued_at"]

    with pytest.raises(ValidationError, match="expires_at must be after issued_at"):
        EmbedTicketClaims.model_validate(payload)


@pytest.mark.parametrize(
    "message",
    [
        {"type": "ready"},
        {"type": "refresh"},
        {
            "type": "setParameters",
            "request_id": "request-1",
            "parameters": {"region": "east"},
        },
        {"type": "getParameters", "request_id": "request-2"},
        {"type": "fullscreen", "request_id": "request-3", "enabled": True},
        {"type": "exportImage", "request_id": "request-4", "format": "png"},
        {
            "type": "error",
            "request_id": "request-5",
            "code": "QUERY_TIMEOUT",
            "message": "Query timed out",
        },
        {
            "type": "aiQuestion",
            "request_id": "request-6",
            "question": "销售额为什么下降？",
        },
    ],
)
def test_embed_message_accepts_supported_variants(message: dict[str, object]) -> None:
    envelope = EmbedMessageEnvelope.model_validate(message)

    assert envelope.root.type == message["type"]


def test_embed_message_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError):
        EmbedMessageEnvelope.model_validate({"type": "unknown"})
