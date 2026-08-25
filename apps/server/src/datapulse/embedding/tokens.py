import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import jwt
from pydantic import ValidationError

from datapulse.contracts.common import JsonValue
from datapulse.contracts.embed import EmbedTicketClaims
from datapulse.screen.access import ScreenAccessPolicyInvalid, normalize_origin

EMBED_AUDIENCE = "datapulse-embed"
MAX_EMBED_TICKET_LIFETIME = timedelta(hours=8)


class EmbedTicketInvalid(ValueError):
    code = "EMBED_TICKET_INVALID"


class EmbedTicketExpired(EmbedTicketInvalid):
    code = "EMBED_TICKET_EXPIRED"


class EmbedTicketLifetimeInvalid(EmbedTicketInvalid):
    code = "EMBED_TICKET_LIFETIME_INVALID"


class EmbedTicketOriginInvalid(EmbedTicketInvalid):
    code = "EMBED_TICKET_ORIGIN_INVALID"


def validate_embed_origin(origin: str) -> str:
    try:
        return normalize_origin(origin)
    except ScreenAccessPolicyInvalid as error:
        raise EmbedTicketOriginInvalid("The embed Origin is invalid.") from error


class EmbedTicketCodec:
    def __init__(
        self,
        *,
        signing_key: bytes,
        id_factory: Callable[[], str] | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if len(signing_key) != 32:
            raise ValueError("The embed signing key must contain exactly 32 bytes.")
        self._signing_key = signing_key
        self._id_factory = id_factory or (lambda: secrets.token_urlsafe(16))
        self._now = now or (lambda: datetime.now(UTC))

    def issue(
        self,
        *,
        screen_id: str,
        allowed_origin: str,
        parameters: dict[str, JsonValue],
        mutable_parameters: tuple[str, ...],
        lifetime: timedelta,
    ) -> str:
        if lifetime <= timedelta(0) or lifetime > MAX_EMBED_TICKET_LIFETIME:
            raise EmbedTicketLifetimeInvalid(
                "Embed tickets must live for no more than eight hours."
            )
        issued_at = self._now()
        return jwt.encode(
            {
                "aud": EMBED_AUDIENCE,
                "exp": int((issued_at + lifetime).timestamp()),
                "iat": int(issued_at.timestamp()),
                "iss": "datapulse",
                "jti": self._id_factory(),
                "mutable_parameters": list(mutable_parameters),
                "origin": validate_embed_origin(allowed_origin),
                "parameters": parameters,
                "screen_id": screen_id,
            },
            self._signing_key,
            algorithm="HS256",
        )

    def verify(
        self,
        token: str,
        *,
        expected_screen_id: str,
    ) -> EmbedTicketClaims:
        try:
            payload = jwt.decode(
                token,
                self._signing_key,
                algorithms=["HS256"],
                audience=EMBED_AUDIENCE,
                issuer="datapulse",
                options={
                    "require": [
                        "aud",
                        "exp",
                        "iat",
                        "iss",
                        "jti",
                        "mutable_parameters",
                        "origin",
                        "parameters",
                        "screen_id",
                    ],
                    "verify_exp": False,
                    "verify_iat": False,
                },
            )
            screen_id = payload["screen_id"]
            origin = payload["origin"]
            parameters = payload["parameters"]
            mutable = payload["mutable_parameters"]
            ticket_id = payload["jti"]
            issued_at = payload["iat"]
            expires_at = payload["exp"]
            if (
                not isinstance(screen_id, str)
                or screen_id != expected_screen_id
                or not isinstance(origin, str)
                or not isinstance(parameters, dict)
                or not isinstance(mutable, list)
                or not all(isinstance(item, str) and item for item in mutable)
                or len(mutable) != len(set(mutable))
                or not isinstance(ticket_id, str)
                or not ticket_id
                or not isinstance(issued_at, int)
                or isinstance(issued_at, bool)
                or not isinstance(expires_at, int)
                or isinstance(expires_at, bool)
            ):
                raise TypeError
            claims = EmbedTicketClaims(
                ticket_id=ticket_id,
                screen_id=screen_id,
                allowed_origin=validate_embed_origin(origin),
                parameters=parameters,
                mutable_parameters=tuple(mutable),
                issued_at=datetime.fromtimestamp(issued_at, UTC),
                expires_at=datetime.fromtimestamp(expires_at, UTC),
            )
        except (
            KeyError,
            TypeError,
            ValueError,
            ValidationError,
            jwt.InvalidTokenError,
        ) as error:
            raise EmbedTicketInvalid("The embed ticket is invalid.") from error
        if claims.expires_at <= self._now():
            raise EmbedTicketExpired("The embed ticket has expired.")
        if (
            claims.issued_at >= claims.expires_at
            or claims.expires_at - claims.issued_at > MAX_EMBED_TICKET_LIFETIME
        ):
            raise EmbedTicketInvalid("The embed ticket dates are invalid.")
        return claims


__all__ = [
    "EMBED_AUDIENCE",
    "MAX_EMBED_TICKET_LIFETIME",
    "EmbedTicketClaims",
    "EmbedTicketCodec",
    "EmbedTicketExpired",
    "EmbedTicketInvalid",
    "EmbedTicketLifetimeInvalid",
    "EmbedTicketOriginInvalid",
    "validate_embed_origin",
]
