import base64
import hmac
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from datapulse.auth.repository import AuthRepository
from datapulse.metadata import AdminAccount, AdminSession


@dataclass(frozen=True)
class CreatedSession:
    session_token: str
    csrf_token: str


class SessionService:
    def __init__(
        self,
        repository: AuthRepository,
        *,
        clock: Callable[[], datetime] | None = None,
        token_factory: Callable[[int], bytes] | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._token_factory = token_factory or secrets.token_bytes

    @staticmethod
    def _encode_token(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode()

    @staticmethod
    def _hash_token(value: str) -> str:
        return sha256(value.encode()).hexdigest()

    async def create(self, *, admin_id: str) -> CreatedSession:
        session_token = self._encode_token(self._token_factory(32))
        csrf_token = self._encode_token(self._token_factory(32))
        now = self._clock()
        await self._repository.save_session(
            AdminSession(
                id=self._hash_token(session_token),
                admin_id=admin_id,
                csrf_token_hash=self._hash_token(csrf_token),
                created_at=now,
                expires_at=now + timedelta(hours=8),
                last_seen_at=now,
            )
        )
        return CreatedSession(session_token=session_token, csrf_token=csrf_token)

    async def authenticate(self, session_token: str) -> AdminAccount | None:
        session_hash = self._hash_token(session_token)
        record = await self._repository.get_session(session_hash)
        now = self._clock()
        if record is None:
            return None
        if record.expires_at <= now:
            await self._repository.delete_session(session_hash)
            return None
        admin = await self._repository.get_admin_by_id(record.admin_id)
        if admin is None or not admin.active:
            return None
        await self._repository.touch_session(session_hash, now)
        return admin

    async def verify_csrf(
        self,
        session_token: str,
        *,
        cookie_token: str,
        header_token: str,
    ) -> bool:
        if not hmac.compare_digest(cookie_token, header_token):
            return False
        session_hash = self._hash_token(session_token)
        record = await self._repository.get_session(session_hash)
        if record is None or record.expires_at <= self._clock():
            return False
        return hmac.compare_digest(
            record.csrf_token_hash,
            self._hash_token(cookie_token),
        )

    async def logout(self, session_token: str) -> None:
        await self._repository.delete_session(self._hash_token(session_token))

    async def revoke_other_sessions(self, admin_id: str, keep_token: str) -> None:
        await self._repository.delete_other_sessions(
            admin_id,
            self._hash_token(keep_token),
        )
