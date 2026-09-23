import json

from pydantic import ValidationError
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from datapulse.contracts.dashboard import DashboardDocument
from datapulse.metadata import DigitalHumanAuditRecord, ScreenRecord
from datapulse.metadata.models import utc_now
from datapulse.screen.access import ScreenAccessPolicy, ScreenAccessPolicyInvalid
from datapulse.screen.models import ScreenResponse


class ScreenNotFound(LookupError):
    pass


class ScreenNameConflict(ValueError):
    pass


class ScreenRevisionConflict(ValueError):
    pass


class ScreenDocumentInvalid(ValueError):
    code = "SCREEN_DOCUMENT_INVALID"


def _canonical_document(document: DashboardDocument) -> dict[str, object]:
    serialized = json.dumps(
        document.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return json.loads(serialized)


class ScreenRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _to_response(record: ScreenRecord) -> ScreenResponse:
        try:
            draft_document = DashboardDocument.model_validate(record.draft_document)
            published_document = (
                DashboardDocument.model_validate(record.published_document)
                if record.published_document is not None
                else None
            )
            access_policy = ScreenAccessPolicy.model_validate(record.access_policy_json or {})
        except (TypeError, ValueError, ValidationError) as error:
            if isinstance(error, ScreenAccessPolicyInvalid):
                raise error
            raise ScreenDocumentInvalid(record.id) from error
        return ScreenResponse(
            id=record.id,
            name=record.name,
            description=record.description,
            draft_document=draft_document,
            draft_revision=record.draft_revision,
            published_document=published_document,
            access_policy=access_policy,
            published_at=record.published_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    async def create(
        self,
        name: str,
        document: DashboardDocument,
        *,
        description: str = "",
        screen_id: str | None = None,
    ) -> ScreenResponse:
        values = {
            "name": name,
            "description": description,
            "draft_document": _canonical_document(document),
        }
        if screen_id is not None:
            values["id"] = screen_id
        record = ScreenRecord(**values)
        try:
            async with self._session_factory.begin() as session:
                session.add(record)
                await session.flush()
                session.add(
                    DigitalHumanAuditRecord(
                        created_at=utc_now(),
                        actor="system",
                        action="screen.created",
                        resource_type="screen",
                        resource_id=record.id,
                        details_json={},
                    )
                )
        except IntegrityError as error:
            raise ScreenNameConflict(name) from error
        return self._to_response(record)

    async def list(self) -> tuple[ScreenResponse, ...]:
        async with self._session_factory() as session:
            records = (
                await session.scalars(
                    select(ScreenRecord).order_by(
                        ScreenRecord.created_at,
                        ScreenRecord.name,
                    )
                )
            ).all()
        return tuple(self._to_response(record) for record in records)

    async def get(self, screen_id: str) -> ScreenResponse:
        async with self._session_factory() as session:
            record = await session.get(ScreenRecord, screen_id)
        if record is None:
            raise ScreenNotFound(screen_id)
        return self._to_response(record)

    async def update_metadata(
        self,
        screen_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        access_policy: ScreenAccessPolicy | None = None,
    ) -> ScreenResponse:
        try:
            async with self._session_factory.begin() as session:
                record = await session.get(ScreenRecord, screen_id)
                if record is None:
                    raise ScreenNotFound(screen_id)
                if name is not None:
                    record.name = name
                if description is not None:
                    record.description = description
                if access_policy is not None:
                    record.access_policy_json = access_policy.model_dump(mode="json")
                record.updated_at = utc_now()
                await session.flush()
        except IntegrityError as error:
            raise ScreenNameConflict(name or "") from error
        return self._to_response(record)

    async def save_draft(
        self,
        screen_id: str,
        *,
        document: DashboardDocument,
        expected_revision: int,
        name: str | None = None,
        description: str | None = None,
        access_policy: ScreenAccessPolicy | None = None,
    ) -> ScreenResponse:
        values: dict[str, object] = {
            "draft_document": _canonical_document(document),
            "draft_revision": ScreenRecord.draft_revision + 1,
            "updated_at": utc_now(),
        }
        if name is not None:
            values["name"] = name
        if description is not None:
            values["description"] = description
        if access_policy is not None:
            values["access_policy_json"] = access_policy.model_dump(mode="json")
        try:
            async with self._session_factory.begin() as session:
                result = await session.execute(
                    update(ScreenRecord)
                    .where(
                        ScreenRecord.id == screen_id,
                        ScreenRecord.draft_revision == expected_revision,
                    )
                    .values(**values)
                )
                if not result.rowcount:
                    exists = await session.scalar(
                        select(ScreenRecord.id).where(ScreenRecord.id == screen_id)
                    )
                    if exists is None:
                        raise ScreenNotFound(screen_id)
                    raise ScreenRevisionConflict(screen_id)
                record = await session.get(ScreenRecord, screen_id)
                session.add(
                    DigitalHumanAuditRecord(
                        created_at=utc_now(),
                        actor="system",
                        action="screen.draft_updated",
                        resource_type="screen",
                        resource_id=screen_id,
                        details_json={"revision": str(expected_revision + 1)},
                    )
                )
        except IntegrityError as error:
            raise ScreenNameConflict(name or "") from error
        if record is None:
            raise ScreenNotFound(screen_id)
        return self._to_response(record)

    async def update_access_policy(
        self,
        screen_id: str,
        *,
        access_policy: ScreenAccessPolicy,
    ) -> ScreenResponse:
        async with self._session_factory.begin() as session:
            record = await session.get(ScreenRecord, screen_id)
            if record is None:
                raise ScreenNotFound(screen_id)
            record.access_policy_json = access_policy.model_dump(mode="json")
            record.updated_at = utc_now()
            await session.flush()
        return self._to_response(record)

    async def publish(
        self,
        screen_id: str,
        *,
        document: DashboardDocument,
        expected_revision: int,
    ) -> ScreenResponse:
        published_at = utc_now()
        async with self._session_factory.begin() as session:
            result = await session.execute(
                update(ScreenRecord)
                .where(
                    ScreenRecord.id == screen_id,
                    ScreenRecord.draft_revision == expected_revision,
                )
                .values(
                    published_document=_canonical_document(document),
                    published_at=published_at,
                    updated_at=published_at,
                )
            )
            if not result.rowcount:
                exists = await session.scalar(
                    select(ScreenRecord.id).where(ScreenRecord.id == screen_id)
                )
                if exists is None:
                    raise ScreenNotFound(screen_id)
                raise ScreenRevisionConflict(screen_id)
            record = await session.get(ScreenRecord, screen_id)
            session.add(
                DigitalHumanAuditRecord(
                    created_at=published_at,
                    actor="system",
                    action="screen.published",
                    resource_type="screen",
                    resource_id=screen_id,
                    details_json={"revision": str(expected_revision)},
                )
            )
        if record is None:
            raise ScreenNotFound(screen_id)
        return self._to_response(record)

    async def delete(self, screen_id: str) -> None:
        async with self._session_factory.begin() as session:
            result = await session.execute(delete(ScreenRecord).where(ScreenRecord.id == screen_id))
            if not result.rowcount:
                raise ScreenNotFound(screen_id)
            session.add(
                DigitalHumanAuditRecord(
                    created_at=utc_now(),
                    actor="system",
                    action="screen.deleted",
                    resource_type="screen",
                    resource_id=screen_id,
                    details_json={},
                )
            )
