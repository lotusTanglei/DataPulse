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
        "ticket_id": "ticket-1",
        "screen_id": "executive-overview",
        "allowed_origin": "https://host.example.com",
        "issued_at": issued_at,
        "expires_at": issued_at + timedelta(hours=1),
        "parameters": {"region": "east"},
        "mutable_parameters": ("region",),
    }


def test_embed_ticket_round_trips_phase_two_claims() -> None:
    ticket = EmbedTicketClaims.model_validate(ticket_payload())

    restored = EmbedTicketClaims.model_validate_json(ticket.model_dump_json())

    assert restored == ticket
    assert restored.ticket_id == "ticket-1"
    assert restored.screen_id == "executive-overview"
    assert restored.mutable_parameters == ("region",)


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


@pytest.mark.parametrize(
    "origin",
    ["http://localhost:5173", "http://127.0.0.1:5173"],
)
def test_embed_ticket_allows_local_http_origins(origin: str) -> None:
    payload = ticket_payload()
    payload["allowed_origin"] = origin

    ticket = EmbedTicketClaims.model_validate(payload)

    assert ticket.allowed_origin == origin


def test_embed_ticket_rejects_expiration_beyond_eight_hours() -> None:
    payload = ticket_payload()
    payload["expires_at"] = payload["issued_at"] + timedelta(hours=8, seconds=1)

    with pytest.raises(ValidationError, match="eight hours"):
        EmbedTicketClaims.model_validate(payload)


def test_embed_ticket_rejects_duplicate_mutable_parameters() -> None:
    payload = ticket_payload()
    payload["mutable_parameters"] = ("region", "region")

    with pytest.raises(ValidationError, match="must be unique"):
        EmbedTicketClaims.model_validate(payload)


@pytest.mark.parametrize(
    "message",
    [
        {"type": "ready", "instance_id": "embed-1", "protocol_version": 1},
        {"type": "refresh", "instance_id": "embed-1"},
        {
            "type": "setParameters",
            "instance_id": "embed-1",
            "request_id": "request-1",
            "parameters": {"region": "east"},
        },
        {
            "type": "getParameters",
            "instance_id": "embed-1",
            "request_id": "request-2",
        },
        {
            "type": "parameters",
            "instance_id": "embed-1",
            "request_id": "request-2",
            "parameters": {"region": "east"},
        },
        {
            "type": "fullscreen",
            "instance_id": "embed-1",
            "request_id": "request-3",
            "enabled": True,
        },
        {
            "type": "ack",
            "instance_id": "embed-1",
            "request_id": "request-3",
        },
        {
            "type": "error",
            "instance_id": "embed-1",
            "request_id": "request-4",
            "code": "QUERY_TIMEOUT",
            "message": "Query timed out",
        },
    ],
)
def test_embed_message_accepts_minimal_sdk_variants(
    message: dict[str, object],
) -> None:
    envelope = EmbedMessageEnvelope.model_validate(message)

    assert envelope.root.type == message["type"]


@pytest.mark.parametrize("message_type", ["exportImage", "aiQuestion", "unknown"])
def test_embed_message_rejects_out_of_scope_variants(message_type: str) -> None:
    with pytest.raises(ValidationError):
        EmbedMessageEnvelope.model_validate(
            {
                "type": message_type,
                "instance_id": "embed-1",
                "request_id": "request-1",
            }
        )
