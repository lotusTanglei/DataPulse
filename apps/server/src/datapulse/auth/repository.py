import hmac
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from datapulse.metadata import AdminAccount, AdminSession, SystemState


class AdminAlreadyExists(Exception):
    pass


class AuthRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_system_state(self) -> SystemState:
        async with self._session_factory() as session:
            state = await session.get(SystemState, 1)
            if state is None:
                state = SystemState(id=1)
                session.add(state)
                await session.commit()
            return state

    async def save_setup_code(self, code_hash: str, expires_at: datetime) -> None:
        async with self._session_factory.begin() as session:
            state = await session.get(SystemState, 1)
            if state is None:
                session.add(
                    SystemState(
                        id=1,
                        setup_code_hash=code_hash,
                        setup_code_expires_at=expires_at,
                    )
                )
            else:
                state.setup_code_hash = code_hash
                state.setup_code_expires_at = expires_at

    async def consume_setup_code(self, code_hash: str, now: datetime) -> bool:
        async with self._session_factory.begin() as session:
            result = await session.execute(
                update(SystemState)
                .where(
                    SystemState.id == 1,
                    SystemState.setup_code_hash == code_hash,
                    SystemState.setup_code_expires_at > now,
                )
                .values(setup_code_hash=None, setup_code_expires_at=None)
            )
            return bool(result.rowcount)

    async def has_admin(self) -> bool:
        async with self._session_factory() as session:
            return (await session.scalar(select(AdminAccount.id).limit(1))) is not None

    async def get_admin_by_username(self, username: str) -> AdminAccount | None:
        async with self._session_factory() as session:
            return await session.scalar(
                select(AdminAccount).where(AdminAccount.username == username)
            )

    async def get_admin_by_id(self, admin_id: str) -> AdminAccount | None:
        async with self._session_factory() as session:
            return await session.get(AdminAccount, admin_id)

    async def update_admin_password(
        self,
        admin_id: str,
        *,
        password_hash: str,
        changed_at: datetime,
    ) -> None:
        async with self._session_factory.begin() as session:
            await session.execute(
                update(AdminAccount)
                .where(AdminAccount.id == admin_id)
                .values(
                    password_hash=password_hash,
                    password_changed_at=changed_at,
                    updated_at=changed_at,
                )
            )

    async def create_admin_from_setup_code(
        self,
        *,
        code_hash: str,
        now: datetime,
        username: str,
        password_hash: str,
    ) -> AdminAccount | None:
        async with self._session_factory.begin() as session:
            if await session.get(AdminAccount, "admin") is not None:
                raise AdminAlreadyExists
            state = await session.get(SystemState, 1, with_for_update=True)
            if (
                state is None
                or state.setup_code_hash is None
                or state.setup_code_expires_at is None
                or state.setup_code_expires_at <= now
                or not hmac.compare_digest(state.setup_code_hash, code_hash)
            ):
                return None
            state.setup_code_hash = None
            state.setup_code_expires_at = None
            admin = AdminAccount(
                id="admin",
                username=username,
                password_hash=password_hash,
                password_changed_at=now,
                created_at=now,
                updated_at=now,
            )
            session.add(admin)
            return admin

    async def save_session(self, record: AdminSession) -> None:
        async with self._session_factory.begin() as session:
            session.add(record)

    async def get_session(self, session_hash: str) -> AdminSession | None:
        async with self._session_factory() as session:
            return await session.get(AdminSession, session_hash)

    async def touch_session(self, session_hash: str, seen_at: datetime) -> None:
        async with self._session_factory.begin() as session:
            await session.execute(
                update(AdminSession)
                .where(AdminSession.id == session_hash)
                .values(last_seen_at=seen_at)
            )

    async def delete_session(self, session_hash: str) -> None:
        async with self._session_factory.begin() as session:
            await session.execute(delete(AdminSession).where(AdminSession.id == session_hash))

    async def delete_other_sessions(self, admin_id: str, keep_hash: str) -> None:
        async with self._session_factory.begin() as session:
            await session.execute(
                delete(AdminSession).where(
                    AdminSession.admin_id == admin_id,
                    AdminSession.id != keep_hash,
                )
            )
