import hashlib
import hmac
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

from datapulse.display.repository import DisplayAccessRepository, DisplayKeyNotFound
from datapulse.display.tokens import (
    DisplaySessionCodec,
    DisplaySessionExpired,
    DisplaySessionInvalid,
)
from datapulse.screen.repository import ScreenNotFound, ScreenRepository

DISPLAY_SESSION_LIFETIME = timedelta(days=30)


class DisplayAccessDenied(ValueError):
    code = "DISPLAY_ACCESS_DENIED"


class DisplayAddressDenied(ValueError):
    code = "DISPLAY_ADDRESS_DENIED"


class DisplayScreenUnavailable(LookupError):
    code = "DISPLAY_SCREEN_UNAVAILABLE"


class DisplaySigningUnavailable(RuntimeError):
    code = "DISPLAY_SIGNING_UNAVAILABLE"


@dataclass(frozen=True)
class DisplayKey:
    screen_id: str
    key_version: int
    plaintext: str


class DisplayAccessService:
    def __init__(
        self,
        *,
        repository: DisplayAccessRepository,
        screen_repository: ScreenRepository,
        codec: DisplaySessionCodec | None,
        key_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._screen_repository = screen_repository
        self._codec = codec
        self._key_factory = key_factory or (lambda: secrets.token_urlsafe(32))

    async def generate_key(self, screen_id: str) -> DisplayKey:
        plaintext = self._key_factory()
        stored = await self._repository.rotate(
            screen_id,
            hashlib.sha256(plaintext.encode()).hexdigest(),
        )
        return DisplayKey(
            screen_id=screen_id,
            key_version=stored.key_version,
            plaintext=plaintext,
        )

    async def exchange(
        self,
        screen_id: str,
        plaintext: str,
        *,
        origin: str | None = None,
        client_ip: str | None = None,
    ) -> str:
        if self._codec is None:
            raise DisplaySigningUnavailable
        screen = await self._screen_repository.get(screen_id)
        if screen.published_document is None:
            raise DisplayScreenUnavailable(screen_id)
        self._ensure_request_allowed(screen, origin=origin, client_ip=client_ip)
        try:
            stored = await self._repository.get(screen_id)
        except DisplayKeyNotFound as error:
            raise DisplayAccessDenied(screen_id) from error
        supplied_hash = hashlib.sha256(plaintext.encode()).hexdigest()
        if not hmac.compare_digest(stored.key_hash, supplied_hash):
            raise DisplayAccessDenied(screen_id)
        return self._codec.issue(
            screen_id=screen_id,
            key_version=stored.key_version,
            lifetime=DISPLAY_SESSION_LIFETIME,
        )

    @staticmethod
    def _ensure_request_allowed(
        screen,
        *,
        origin: str | None,
        client_ip: str | None,
    ) -> None:
        if not screen.access_policy.allows_request(origin=origin, client_ip=client_ip):
            raise DisplayAddressDenied(screen.id)

    async def authorize_request(
        self,
        screen_id: str,
        *,
        origin: str | None,
        client_ip: str | None,
    ) -> None:
        screen = await self._screen_repository.get(screen_id)
        if screen.published_document is None:
            raise DisplayScreenUnavailable(screen_id)
        self._ensure_request_allowed(screen, origin=origin, client_ip=client_ip)

    async def authenticate(
        self,
        screen_id: str,
        token: str,
        *,
        origin: str | None = None,
        client_ip: str | None = None,
    ) -> str | Literal[False]:
        if self._codec is None:
            return False
        try:
            claims = self._codec.verify(token)
            if claims.screen_id != screen_id:
                return False
            stored = await self._repository.get(screen_id)
            if stored.key_version != claims.key_version:
                return False
            screen = await self._screen_repository.get(screen_id)
            if screen.published_document is None:
                return False
            self._ensure_request_allowed(screen, origin=origin, client_ip=client_ip)
        except (
            DisplayKeyNotFound,
            DisplaySessionExpired,
            DisplaySessionInvalid,
            ScreenNotFound,
        ):
            return False
        return self._codec.issue(
            screen_id=screen_id,
            key_version=stored.key_version,
            lifetime=DISPLAY_SESSION_LIFETIME,
        )


__all__ = [
    "DISPLAY_SESSION_LIFETIME",
    "DisplayAccessDenied",
    "DisplayAddressDenied",
    "DisplayAccessService",
    "DisplayKey",
    "DisplayScreenUnavailable",
    "DisplaySigningUnavailable",
]
