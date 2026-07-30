import base64
import hashlib
import hmac
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


class DisplaySessionInvalid(ValueError):
    pass


class DisplaySessionExpired(DisplaySessionInvalid):
    pass


@dataclass(frozen=True)
class DisplaySessionClaims:
    screen_id: str
    key_version: int
    issued_at: datetime
    expires_at: datetime


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.b64decode(
            f"{value}{padding}",
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, TypeError) as error:
        raise DisplaySessionInvalid("The display session is malformed.") from error


class DisplaySessionCodec:
    def __init__(
        self,
        *,
        signing_key: bytes,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if len(signing_key) != 32:
            raise ValueError("The display signing key must contain exactly 32 bytes.")
        self._signing_key = signing_key
        self._now = now or (lambda: datetime.now(UTC))

    def issue(
        self,
        *,
        screen_id: str,
        key_version: int,
        lifetime: timedelta,
    ) -> str:
        issued_at = self._now()
        payload = json.dumps(
            {
                "expires_at": int((issued_at + lifetime).timestamp()),
                "issued_at": int(issued_at.timestamp()),
                "key_version": key_version,
                "screen_id": screen_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        encoded_payload = _encode(payload)
        signature = hmac.new(
            self._signing_key,
            encoded_payload.encode(),
            hashlib.sha256,
        ).digest()
        return f"{encoded_payload}.{_encode(signature)}"

    def verify(self, token: str) -> DisplaySessionClaims:
        try:
            encoded_payload, encoded_signature = token.split(".", 1)
        except ValueError as error:
            raise DisplaySessionInvalid("The display session is malformed.") from error
        expected = hmac.new(
            self._signing_key,
            encoded_payload.encode(),
            hashlib.sha256,
        ).digest()
        supplied = _decode(encoded_signature)
        if not hmac.compare_digest(expected, supplied):
            raise DisplaySessionInvalid("The display session signature is invalid.")
        try:
            payload = json.loads(_decode(encoded_payload))
            screen_id = payload["screen_id"]
            key_version = payload["key_version"]
            issued_at = payload["issued_at"]
            expires_at = payload["expires_at"]
            if (
                not isinstance(screen_id, str)
                or not screen_id
                or not isinstance(key_version, int)
                or isinstance(key_version, bool)
                or not isinstance(issued_at, int)
                or isinstance(issued_at, bool)
                or not isinstance(expires_at, int)
                or isinstance(expires_at, bool)
            ):
                raise TypeError
            claims = DisplaySessionClaims(
                screen_id=screen_id,
                key_version=key_version,
                issued_at=datetime.fromtimestamp(issued_at, UTC),
                expires_at=datetime.fromtimestamp(expires_at, UTC),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise DisplaySessionInvalid("The display session claims are invalid.") from error
        if claims.expires_at <= self._now():
            raise DisplaySessionExpired("The display session has expired.")
        if claims.issued_at >= claims.expires_at:
            raise DisplaySessionInvalid("The display session dates are invalid.")
        return claims


__all__ = [
    "DisplaySessionClaims",
    "DisplaySessionCodec",
    "DisplaySessionExpired",
    "DisplaySessionInvalid",
]
