import hmac
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from datapulse.auth.password import hash_password
from datapulse.auth.repository import AdminAlreadyExists, AuthRepository
from datapulse.metadata import AdminAccount


class BootstrapUnavailable(Exception):
    pass


class InvalidSetupCode(Exception):
    pass


class BootstrapService:
    def __init__(
        self,
        repository: AuthRepository,
        *,
        clock: Callable[[], datetime] | None = None,
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(24))

    @staticmethod
    def _hash_code(code: str) -> str:
        return sha256(code.encode()).hexdigest()

    async def issue_code(self) -> str:
        if await self._repository.has_admin():
            raise BootstrapUnavailable
        raw_code = self._token_factory()
        await self._repository.save_setup_code(
            self._hash_code(raw_code),
            self._clock() + timedelta(minutes=30),
        )
        return raw_code

    async def consume_code(self, code: str) -> bool:
        state = await self._repository.get_system_state()
        supplied_hash = self._hash_code(code)
        if (
            state.setup_code_hash is None
            or state.setup_code_expires_at is None
            or state.setup_code_expires_at <= self._clock()
            or not hmac.compare_digest(state.setup_code_hash, supplied_hash)
        ):
            return False
        return await self._repository.consume_setup_code(supplied_hash, self._clock())

    async def create_admin(
        self,
        *,
        code: str,
        username: str,
        password: str,
    ) -> AdminAccount:
        try:
            admin = await self._repository.create_admin_from_setup_code(
                code_hash=self._hash_code(code),
                now=self._clock(),
                username=username,
                password_hash=hash_password(password),
            )
        except AdminAlreadyExists as error:
            raise BootstrapUnavailable from error
        if admin is None:
            raise InvalidSetupCode
        return admin
