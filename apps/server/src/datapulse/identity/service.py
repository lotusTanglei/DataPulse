from collections.abc import Sequence
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from datapulse.auth.password import hash_password
from datapulse.errors import DataPulseError
from datapulse.identity.models import (
    AuditResponse,
    GrantRequest,
    SpeechProviderOption,
    UserCreate,
    UserPatch,
    UserResponse,
)
from datapulse.metadata.models import (
    AdminAccount,
    AdminSession,
    DatasetRecord,
    DataSourceRecord,
    DigitalHumanProviderRecord,
    FileAssetRecord,
    IdentityAuditRecord,
    ResourceGrantRecord,
    ResourceOwnershipRecord,
    ScreenAssetRecord,
    ScreenRecord,
    SpeechPlanRecord,
    SpeechTaskRecord,
    SystemState,
    utc_now,
)

RESOURCE_MODELS = {
    "datasource": DataSourceRecord,
    "dataset": DatasetRecord,
    "file": FileAssetRecord,
    "asset": ScreenAssetRecord,
    "screen": ScreenRecord,
}


def unavailable() -> DataPulseError:
    return DataPulseError(
        code="RESOURCE_NOT_FOUND", message="The resource does not exist.", status_code=404
    )


def forbidden() -> DataPulseError:
    return DataPulseError(
        code="IDENTITY_FORBIDDEN", message="This action is not permitted.", status_code=403
    )


class IdentityService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def require_administrator(user: AdminAccount) -> None:
        if not user.active or user.role != "admin":
            raise forbidden()

    @staticmethod
    def require_creator(user: AdminAccount) -> None:
        if not user.active or user.role not in {"admin", "editor"}:
            raise forbidden()

    @staticmethod
    def _audit(
        session: AsyncSession,
        actor: AdminAccount,
        action: str,
        request_id: str,
        *,
        resource_type: str | None = None,
        resource_id: str | None = None,
        subject_id: str | None = None,
    ) -> None:
        session.add(
            IdentityAuditRecord(
                actor_id=actor.id,
                action=action,
                request_id=request_id,
                resource_type=resource_type,
                resource_id=resource_id,
                subject_id=subject_id,
            )
        )

    async def users(self, actor: AdminAccount) -> tuple[UserResponse, ...]:
        self.require_administrator(actor)
        async with self._session_factory() as session:
            rows = (
                await session.scalars(select(AdminAccount).order_by(AdminAccount.created_at))
            ).all()
            return tuple(UserResponse.model_validate(row) for row in rows)

    async def directory(self) -> tuple[dict[str, str], ...]:
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(AdminAccount)
                    .where(AdminAccount.active.is_(True))
                    .order_by(AdminAccount.username)
                )
            ).all()
            return tuple({"id": row.id, "username": row.username} for row in rows)

    async def create_user(
        self, actor: AdminAccount, payload: UserCreate, request_id: str
    ) -> UserResponse:
        self.require_administrator(actor)
        row = AdminAccount(
            id=str(uuid4()),
            username=payload.username,
            role=payload.role,
            active=True,
            password_hash=hash_password(payload.password),
        )
        try:
            async with self._session_factory.begin() as session:
                session.add(row)
                await session.flush()
                self._audit(session, actor, "user.create", request_id, subject_id=row.id)
        except IntegrityError as error:
            raise DataPulseError(
                code="IDENTITY_USERNAME_CONFLICT",
                message="The username is already in use.",
                status_code=409,
            ) from error
        return UserResponse.model_validate(row)

    async def update_user(
        self, actor: AdminAccount, user_id: str, payload: UserPatch, request_id: str
    ) -> UserResponse:
        self.require_administrator(actor)
        # Lock a singleton before reading the admin count. This serializes demotions
        # across processes, including SQLite where SELECT FOR UPDATE is ignored.
        async with self._session_factory.begin() as session:
            await session.execute(update(SystemState).where(SystemState.id == 1).values(id=1))
            row = await session.get(AdminAccount, user_id)
            if row is None:
                raise unavailable()
            if (
                row.active
                and row.role == "admin"
                and (payload.active is False or payload.role not in {None, "admin"})
            ):
                admins = (
                    await session.scalars(
                        select(AdminAccount.id).where(
                            AdminAccount.active.is_(True), AdminAccount.role == "admin"
                        )
                    )
                ).all()
                if len(admins) <= 1:
                    raise DataPulseError(
                        code="IDENTITY_LAST_ADMIN",
                        message="At least one active administrator is required.",
                        status_code=409,
                    )
            revoke = False
            if payload.role is not None and row.role != payload.role:
                row.role = payload.role
                revoke = True
            if payload.active is not None and row.active != payload.active:
                row.active = payload.active
                revoke = True
            if payload.password is not None:
                row.password_hash = hash_password(payload.password)
                row.password_changed_at = utc_now()
                revoke = True
                self._audit(session, actor, "user.password_reset", request_id, subject_id=row.id)
            if revoke:
                await session.execute(delete(AdminSession).where(AdminSession.admin_id == user_id))
            row.updated_at = utc_now()
            self._audit(session, actor, "user.update", request_id, subject_id=row.id)
            await session.flush()
        return UserResponse.model_validate(row)

    async def audit(self, actor: AdminAccount, limit: int = 100) -> tuple[AuditResponse, ...]:
        self.require_administrator(actor)
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(IdentityAuditRecord)
                    .order_by(IdentityAuditRecord.created_at.desc())
                    .limit(limit)
                )
            ).all()
            return tuple(AuditResponse.model_validate(row) for row in rows)

    async def can_access(
        self, user: AdminAccount, resource_type: str, resource_id: str, permission: str = "read"
    ) -> bool:
        if not user.active or resource_type not in RESOURCE_MODELS:
            return False
        async with self._session_factory() as session:
            if await session.get(RESOURCE_MODELS[resource_type], resource_id) is None:
                return False
            if user.role == "admin":
                return True
            if user.role not in {"editor", "viewer"} or (
                user.role == "viewer" and permission != "read"
            ):
                return False
            owner = await session.get(ResourceOwnershipRecord, (resource_type, resource_id))
            if owner is not None and owner.owner_id == user.id:
                return True
            if permission == "manage":
                return False
            grant = await session.get(ResourceGrantRecord, (resource_type, resource_id, user.id))
            levels = {"read": 1, "write": 2, "publish": 3}
            return grant is not None and levels.get(grant.permission, 0) >= levels.get(
                permission, 99
            )

    async def require_access(
        self, user: AdminAccount, resource_type: str, resource_id: str, permission: str = "read"
    ) -> None:
        if not await self.can_access(user, resource_type, resource_id, permission):
            raise unavailable()

    async def register_owner(
        self, user: AdminAccount, resource_type: str, resource_id: str
    ) -> None:
        async with self._session_factory.begin() as session:
            # Ingestion may return an existing content-addressed resource. Never
            # overwrite its owner when another account uploads identical bytes.
            if await session.get(ResourceOwnershipRecord, (resource_type, resource_id)) is None:
                session.add(
                    ResourceOwnershipRecord(
                        resource_type=resource_type, resource_id=resource_id, owner_id=user.id
                    )
                )

    async def visible_ids(self, user: AdminAccount, resource_type: str) -> set[str] | None:
        if user.role == "admin":
            return None
        async with self._session_factory() as session:
            owned = set(
                (
                    await session.scalars(
                        select(ResourceOwnershipRecord.resource_id).where(
                            ResourceOwnershipRecord.resource_type == resource_type,
                            ResourceOwnershipRecord.owner_id == user.id,
                        )
                    )
                ).all()
            )
            shared = set(
                (
                    await session.scalars(
                        select(ResourceGrantRecord.resource_id).where(
                            ResourceGrantRecord.resource_type == resource_type,
                            ResourceGrantRecord.user_id == user.id,
                        )
                    )
                ).all()
            )
        return owned | shared

    async def filter_visible(
        self, user: AdminAccount, resource_type: str, rows: Sequence[Any], *, id_field: str = "id"
    ) -> tuple[Any, ...]:
        visible = await self.visible_ids(user, resource_type)
        if visible is None:
            return tuple(rows)
        result = []
        for row in rows:
            identifier = getattr(row, id_field)
            if identifier not in visible:
                continue
            try:
                # Lists expose definitions and names too; keep their visibility
                # consistent with detail reads after a dependency is revoked.
                await self.check_stored_references(user, resource_type, identifier)
            except DataPulseError as error:
                if error.code == "RESOURCE_NOT_FOUND":
                    continue
                raise
            result.append(row)
        return tuple(result)

    async def check_references(
        self,
        user: AdminAccount,
        payload: object,
        *,
        file_context: bool = False,
        _seen: set[tuple[str, str]] | None = None,
    ) -> None:
        if user.role == "admin":
            return
        seen = _seen if _seen is not None else set()
        refs: set[tuple[str, str]] = set()

        def collect(value: object, in_file: bool = False) -> None:
            if isinstance(value, dict):
                in_file = in_file or value.get("kind") == "file"
                for key, item in value.items():
                    kind = {
                        "dataset_id": "dataset",
                        "data_source_id": "datasource",
                        "datasource_id": "datasource",
                        "file_asset_id": "file",
                    }.get(key)
                    if key == "asset_id" or key.endswith("_asset_id"):
                        kind = "file" if key == "file_asset_id" or in_file else "asset"
                    if kind and isinstance(item, str) and item:
                        refs.add((kind, item))
                    if key == "dataset_ids" and isinstance(item, list):
                        refs.update(
                            ("dataset", identifier)
                            for identifier in item
                            if isinstance(identifier, str)
                        )
                    collect(item, in_file)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    collect(item, in_file)

        collect(payload, file_context)
        for kind, identifier in sorted(refs - seen):
            seen.add((kind, identifier))
            await self.require_access(user, kind, identifier)
            if kind == "dataset":
                await self.check_stored_references(user, kind, identifier, _seen=seen)

    async def check_stored_references(
        self,
        user: AdminAccount,
        kind: str,
        identifier: str,
        *,
        _seen: set[tuple[str, str]] | None = None,
    ) -> None:
        if user.role == "admin" or kind not in {"screen", "dataset"}:
            return
        async with self._session_factory() as session:
            row = await session.get(RESOURCE_MODELS[kind], identifier)
        if row is None:
            raise unavailable()
        if kind == "screen":
            await self.check_references(user, row.draft_document, _seen=_seen)
            await self.check_references(user, row.published_document, _seen=_seen)
        else:
            await self.check_references(user, row.definition_json, _seen=_seen)

    async def grants(
        self, user: AdminAccount, kind: str, identifier: str
    ) -> tuple[GrantRequest, ...]:
        await self.require_access(user, kind, identifier, "manage")
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(ResourceGrantRecord).where(
                        ResourceGrantRecord.resource_type == kind,
                        ResourceGrantRecord.resource_id == identifier,
                    )
                )
            ).all()
            return tuple(
                GrantRequest(
                    resource_type=row.resource_type,
                    resource_id=row.resource_id,
                    user_id=row.user_id,
                    permission=row.permission,
                )
                for row in rows
            )

    async def set_grant(
        self, actor: AdminAccount, grant: GrantRequest, request_id: str
    ) -> GrantRequest:
        await self.require_access(actor, grant.resource_type, grant.resource_id, "manage")
        async with self._session_factory.begin() as session:
            target = await session.get(AdminAccount, grant.user_id)
            if target is None or not target.active:
                raise unavailable()
            row = await session.get(
                ResourceGrantRecord, (grant.resource_type, grant.resource_id, grant.user_id)
            )
            if row is None:
                session.add(ResourceGrantRecord(**grant.model_dump()))
            else:
                row.permission = grant.permission
            self._audit(
                session,
                actor,
                "grant.set",
                request_id,
                resource_type=grant.resource_type,
                resource_id=grant.resource_id,
                subject_id=grant.user_id,
            )
        return grant

    async def revoke_grant(
        self, actor: AdminAccount, kind: str, identifier: str, user_id: str, request_id: str
    ) -> None:
        await self.require_access(actor, kind, identifier, "manage")
        async with self._session_factory.begin() as session:
            await session.execute(
                delete(ResourceGrantRecord).where(
                    ResourceGrantRecord.resource_type == kind,
                    ResourceGrantRecord.resource_id == identifier,
                    ResourceGrantRecord.user_id == user_id,
                )
            )
            self._audit(
                session,
                actor,
                "grant.revoke",
                request_id,
                resource_type=kind,
                resource_id=identifier,
                subject_id=user_id,
            )

    async def speech_provider_directory(
        self, user: AdminAccount
    ) -> tuple[SpeechProviderOption, ...]:
        self.require_creator(user)
        async with self._session_factory() as session:
            providers = (
                await session.scalars(
                    select(DigitalHumanProviderRecord)
                    .where(
                        DigitalHumanProviderRecord.enabled.is_(True),
                        DigitalHumanProviderRecord.base_url != "",
                        DigitalHumanProviderRecord.secret_envelope.is_not(None),
                    )
                    .order_by(DigitalHumanProviderRecord.name)
                )
            ).all()
            return tuple(
                SpeechProviderOption(
                    id=row.id, name=row.name, language=row.language, default_voice=row.default_voice
                )
                for row in providers
            )

    async def require_speech_provider(self, user: AdminAccount, provider_id: str) -> None:
        self.require_creator(user)
        if provider_id not in {item.id for item in await self.speech_provider_directory(user)}:
            raise unavailable()

    async def require_speech_scope(
        self, user: AdminAccount, screen_id: str, component_id: str, provider_id: str
    ) -> None:
        self.require_creator(user)
        if not all(
            isinstance(value, str) and value for value in (screen_id, component_id, provider_id)
        ):
            raise unavailable()
        await self.require_access(user, "screen", screen_id, "write")
        await self.check_stored_references(user, "screen", screen_id)
        async with self._session_factory() as session:
            screen = await session.get(ScreenRecord, screen_id)
        if screen is None or not any(
            item.get("id") == component_id
            and item.get("type") == "builtin.digital_human"
            and not item.get("state", {}).get("hidden", False)
            for item in screen.draft_document.get("components", [])
            if isinstance(item, dict)
        ):
            raise unavailable()
        await self.require_speech_provider(user, provider_id)

    async def require_speech_plan(
        self, user: AdminAccount, *, plan_id: str | None = None, task_id: str | None = None
    ) -> None:
        async with self._session_factory() as session:
            if task_id is not None:
                task = await session.get(SpeechTaskRecord, task_id)
                if task is None:
                    raise unavailable()
                plan_id = task.plan_id
            plan = await session.get(SpeechPlanRecord, plan_id)
            owner = await session.get(ResourceOwnershipRecord, ("speech_plan", plan_id))
        if plan is None or owner is None or owner.owner_id != user.id:
            raise unavailable()
        await self.require_speech_scope(user, plan.screen_id, plan.component_id, plan.provider_id)

    async def authorize_speech_asset(
        self, user: AdminAccount, task_id: str, request_id: str
    ) -> None:
        # A task creator owns newly generated media. Identical cached speech may
        # reuse media owned by an earlier creator, so grant only read in that case.
        async with self._session_factory.begin() as session:
            task = await session.get(SpeechTaskRecord, task_id)
            if task is None or not task.asset_id or task.status != "succeeded":
                return
            plan_owner = await session.get(ResourceOwnershipRecord, ("speech_plan", task.plan_id))
            if plan_owner is None or (user.role != "admin" and plan_owner.owner_id != user.id):
                return
            if await session.get(ScreenAssetRecord, task.asset_id) is None:
                return
            target_id = plan_owner.owner_id
            owner = await session.get(ResourceOwnershipRecord, ("asset", task.asset_id))
            if owner is None:
                session.add(
                    ResourceOwnershipRecord(
                        resource_type="asset", resource_id=task.asset_id, owner_id=target_id
                    )
                )
            elif owner.owner_id != target_id:
                existing = await session.get(
                    ResourceGrantRecord, ("asset", task.asset_id, target_id)
                )
                if existing is not None:
                    return
                session.add(
                    ResourceGrantRecord(
                        resource_type="asset",
                        resource_id=task.asset_id,
                        user_id=target_id,
                        permission="read",
                    )
                )
            else:
                return
            self._audit(
                session,
                user,
                "speech.asset_read",
                request_id,
                resource_type="asset",
                resource_id=task.asset_id,
                subject_id=target_id,
            )
