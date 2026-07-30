import hashlib
import hmac
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from datapulse.contracts.common import JsonValue
from datapulse.contracts.embed import EmbedTicketClaims
from datapulse.embedding.repository import EmbedAccessRepository, EmbedApiKeyNotFound
from datapulse.embedding.tokens import EmbedTicketCodec
from datapulse.screen.repository import ScreenNotFound, ScreenRepository
from datapulse.screen.runtime import ScreenParameterInvalid, resolve_parameters


class EmbedApiKeyDenied(ValueError):
    code = "EMBED_API_KEY_DENIED"


class EmbedParameterDenied(ValueError):
    code = "EMBED_PARAMETER_DENIED"


class EmbedScreenUnavailable(LookupError):
    code = "EMBED_SCREEN_UNAVAILABLE"


class EmbedSigningUnavailable(RuntimeError):
    code = "EMBED_SIGNING_UNAVAILABLE"


@dataclass(frozen=True)
class EmbedApiKey:
    key_version: int
    plaintext: str


class EmbedService:
    def __init__(
        self,
        *,
        repository: EmbedAccessRepository,
        screen_repository: ScreenRepository,
        codec: EmbedTicketCodec | None,
        key_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._screen_repository = screen_repository
        self._codec = codec
        self._key_factory = key_factory or (lambda: secrets.token_urlsafe(32))

    async def rotate_api_key(self) -> EmbedApiKey:
        plaintext = self._key_factory()
        stored = await self._repository.rotate(
            hashlib.sha256(plaintext.encode()).hexdigest()
        )
        return EmbedApiKey(
            key_version=stored.key_version,
            plaintext=plaintext,
        )

    async def issue_ticket(
        self,
        *,
        api_key: str,
        screen_id: str,
        allowed_origin: str,
        parameters: dict[str, JsonValue],
        mutable_parameters: tuple[str, ...],
        lifetime: timedelta,
    ) -> str:
        if self._codec is None:
            raise EmbedSigningUnavailable
        try:
            stored = await self._repository.get()
        except EmbedApiKeyNotFound as error:
            raise EmbedApiKeyDenied from error
        supplied_hash = hashlib.sha256(api_key.encode()).hexdigest()
        if not hmac.compare_digest(stored.api_key_hash, supplied_hash):
            raise EmbedApiKeyDenied
        screen = await self._screen_repository.get(screen_id)
        if screen.published_document is None:
            raise EmbedScreenUnavailable(screen_id)
        try:
            resolved = resolve_parameters(screen.published_document, parameters)
        except ScreenParameterInvalid as error:
            raise EmbedParameterDenied from error
        definitions = {
            parameter.name: parameter
            for parameter in screen.published_document.parameters
        }
        if any(
            name not in definitions or not definitions[name].mutable
            for name in mutable_parameters
        ):
            raise EmbedParameterDenied
        return self._codec.issue(
            screen_id=screen_id,
            allowed_origin=allowed_origin,
            parameters=resolved,
            mutable_parameters=mutable_parameters,
            lifetime=lifetime,
        )

    async def authorize(
        self,
        ticket: str,
        *,
        screen_id: str,
    ) -> EmbedTicketClaims:
        if self._codec is None:
            raise EmbedSigningUnavailable
        claims = self._codec.verify(ticket, expected_screen_id=screen_id)
        try:
            screen = await self._screen_repository.get(screen_id)
        except ScreenNotFound as error:
            raise EmbedScreenUnavailable(screen_id) from error
        if screen.published_document is None:
            raise EmbedScreenUnavailable(screen_id)
        return claims

    @staticmethod
    def resolve_parameters(
        claims: EmbedTicketClaims,
        supplied: dict[str, JsonValue],
    ) -> dict[str, JsonValue]:
        if not set(supplied) <= set(claims.mutable_parameters):
            raise EmbedParameterDenied
        return {**claims.parameters, **supplied}


__all__ = [
    "EmbedApiKey",
    "EmbedApiKeyDenied",
    "EmbedParameterDenied",
    "EmbedScreenUnavailable",
    "EmbedService",
    "EmbedSigningUnavailable",
]
