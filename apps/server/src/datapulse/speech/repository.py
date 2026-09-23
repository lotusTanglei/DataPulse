from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from datapulse.contracts.speech import (
    DigitalHumanAuditResponse,
    DigitalHumanCostReportResponse,
    DigitalHumanCostReportRow,
    DigitalHumanPlaybackDiagnosticResponse,
    DigitalHumanProviderCreate,
    DigitalHumanProviderHealthResponse,
    DigitalHumanProviderResponse,
    DigitalHumanProviderUpdate,
    DigitalHumanSettingsResponse,
    DigitalHumanSettingsUpdate,
    DigitalHumanUsageResponse,
    SpeechPlanRequest,
    SpeechPlanResponse,
    SpeechTaskResponse,
)
from datapulse.datasource.secrets import SecretEnvelope
from datapulse.metadata import (
    DigitalHumanAuditRecord,
    DigitalHumanProviderHealthRecord,
    DigitalHumanProviderRecord,
    DigitalHumanSettingsRecord,
    DigitalHumanUsageRecord,
    SpeechPlanRecord,
    SpeechTaskRecord,
)


class SpeechProviderNotFound(LookupError):
    pass


class SpeechTaskNotFound(LookupError):
    pass


class SpeechProviderNameConflict(ValueError):
    pass


class SpeechQuotaRejected(RuntimeError):
    """A quota condition rejected an atomic database transition."""


class SpeechRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._factory = session_factory
        self._id_factory = id_factory or (lambda: str(uuid4()))

    @asynccontextmanager
    async def _quota_session(self) -> AsyncIterator[AsyncSession]:
        """Serialize admissions and quota reconciliation across processes."""
        async with self._factory.begin() as session:
            if session.get_bind().dialect.name == "sqlite":
                await session.execute(text("BEGIN IMMEDIATE"))
            else:
                await session.execute(
                    postgres_insert(DigitalHumanSettingsRecord)
                    .values(id=1)
                    .on_conflict_do_nothing(index_elements=["id"])
                )
                await session.execute(
                    select(DigitalHumanSettingsRecord.id)
                    .where(DigitalHumanSettingsRecord.id == 1)
                    .with_for_update()
                )
            record = await session.get(DigitalHumanSettingsRecord, 1)
            if record is None:
                session.add(DigitalHumanSettingsRecord(id=1))
                await session.flush()
            yield session

    @staticmethod
    def _period(now: datetime) -> datetime:
        return now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    async def _audio_used(self, session: AsyncSession, period: datetime) -> float:
        return float(
            await session.scalar(
                select(func.sum(DigitalHumanUsageRecord.generated_seconds)).where(
                    DigitalHumanUsageRecord.period_start == period
                )
            )
            or 0
        )

    def _audit(
        self,
        session: AsyncSession,
        *,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict[str, str] | None = None,
    ) -> None:
        session.add(
            DigitalHumanAuditRecord(
                id=self._id_factory(),
                created_at=datetime.now(UTC),
                actor="system",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details_json=details or {},
            )
        )

    @staticmethod
    def _provider(
        record: DigitalHumanProviderRecord,
        *,
        now: datetime | None = None,
    ) -> DigitalHumanProviderResponse:
        now = now or datetime.now(UTC)
        if record.secret_envelope is None:
            health_status = "unconfigured"
        elif not record.enabled:
            health_status = "disabled"
        elif record.circuit_open_until is not None and record.circuit_open_until > now:
            health_status = "open"
        elif record.consecutive_failures:
            health_status = "degraded"
        else:
            health_status = "healthy"
        return DigitalHumanProviderResponse(
            id=record.id,
            name=record.name,
            provider_type=record.provider_type,
            base_url=record.base_url,
            default_voice=record.default_voice,
            language=record.language,
            enabled=record.enabled,
            configured=record.secret_envelope is not None,
            cost_per_minute=record.cost_per_minute,
            provider_version=record.provider_version,
            health_status=health_status,
            consecutive_failures=record.consecutive_failures,
            circuit_open_until=record.circuit_open_until,
            last_checked_at=record.last_checked_at,
            last_latency_ms=record.last_latency_ms,
            last_error_code=record.last_error_code,
        )

    async def list_providers(self) -> tuple[DigitalHumanProviderResponse, ...]:
        async with self._factory() as session:
            records = await session.scalars(
                select(DigitalHumanProviderRecord).order_by(DigitalHumanProviderRecord.name)
            )
            return tuple(self._provider(record) for record in records)

    @staticmethod
    def _settings(record: DigitalHumanSettingsRecord) -> DigitalHumanSettingsResponse:
        return DigitalHumanSettingsResponse.model_validate(record, from_attributes=True)

    async def get_settings(self) -> DigitalHumanSettingsResponse:
        async with self._quota_session() as session:
            record = await session.get(DigitalHumanSettingsRecord, 1)
            if record is None:
                record = DigitalHumanSettingsRecord(id=1)
                session.add(record)
                await session.flush()
            return self._settings(record)

    async def update_settings(
        self, data: DigitalHumanSettingsUpdate
    ) -> DigitalHumanSettingsResponse:
        async with self._quota_session() as session:
            record = await session.get(DigitalHumanSettingsRecord, 1)
            if record is None:
                record = DigitalHumanSettingsRecord(id=1)
                session.add(record)
                await session.flush()
            for name, value in data.model_dump(exclude_unset=True).items():
                setattr(record, name, value)
            await session.flush()
            self._audit(
                session,
                action="settings.updated",
                resource_type="settings",
                resource_id="global",
                details={"fields": ",".join(data.model_dump(exclude_unset=True))},
            )
            return self._settings(record)

    async def provider_record(self, provider_id: str) -> DigitalHumanProviderRecord:
        async with self._factory() as session:
            record = await session.get(DigitalHumanProviderRecord, provider_id)
            if record is None:
                raise SpeechProviderNotFound(provider_id)
            return record

    async def create_provider(
        self,
        data: DigitalHumanProviderCreate,
        envelope: SecretEnvelope | None,
        *,
        provider_id: str | None = None,
    ) -> DigitalHumanProviderResponse:
        record = DigitalHumanProviderRecord(
            id=provider_id or self._id_factory(),
            name=data.name,
            provider_type=data.provider_type,
            base_url=data.base_url,
            secret_envelope=envelope.model_dump_json() if envelope else None,
            default_voice=data.default_voice,
            language=data.language,
            enabled=data.enabled,
            cost_per_minute=data.cost_per_minute,
            provider_version=data.provider_version,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        try:
            async with self._factory.begin() as session:
                session.add(record)
                await session.flush()
                self._audit(
                    session,
                    action="provider.created",
                    resource_type="provider",
                    resource_id=record.id,
                    details={"provider_type": record.provider_type},
                )
        except IntegrityError as error:
            raise SpeechProviderNameConflict(data.name) from error
        return self._provider(record)

    async def update_provider(
        self,
        provider_id: str,
        data: DigitalHumanProviderUpdate,
        envelope: SecretEnvelope | None,
        *,
        clear_secret: bool,
    ) -> DigitalHumanProviderResponse:
        async with self._factory.begin() as session:
            record = await session.get(DigitalHumanProviderRecord, provider_id)
            if record is None:
                raise SpeechProviderNotFound(provider_id)
            for key in (
                "name",
                "provider_type",
                "base_url",
                "default_voice",
                "language",
                "enabled",
                "cost_per_minute",
                "provider_version",
            ):
                value = getattr(data, key)
                if value is not None:
                    setattr(record, key, value)
            if clear_secret:
                record.secret_envelope = None
            elif envelope is not None:
                record.secret_envelope = envelope.model_dump_json()
            await session.flush()
            self._audit(
                session,
                action="provider.updated",
                resource_type="provider",
                resource_id=record.id,
                details={"enabled": str(record.enabled)},
            )
            return self._provider(record)

    async def delete_provider(self, provider_id: str) -> None:
        async with self._factory.begin() as session:
            record = await session.get(DigitalHumanProviderRecord, provider_id)
            if record is None:
                raise SpeechProviderNotFound(provider_id)
            self._audit(
                session,
                action="provider.deleted",
                resource_type="provider",
                resource_id=provider_id,
            )
            await session.delete(record)

    async def create_plan(
        self, data: SpeechPlanRequest, *, content_hash: str, provider_version: str = "v1"
    ) -> SpeechPlanResponse:
        record = SpeechPlanRecord(
            id=self._id_factory(),
            screen_id=data.screen_id,
            component_id=data.component_id,
            text=data.text,
            language=data.language,
            provider_id=data.provider_id,
            voice=data.voice,
            rate=data.rate,
            pitch=data.pitch,
            volume=data.volume,
            provider_version=provider_version,
            content_hash=content_hash,
            created_at=datetime.now(UTC),
        )
        async with self._factory.begin() as session:
            session.add(record)
            await session.flush()
        return SpeechPlanResponse.model_validate(record, from_attributes=True)

    async def create_task(
        self,
        plan: SpeechPlanResponse,
        *,
        source: str = "runtime",
        priority: int = 0,
        expires_at: datetime | None = None,
        now: datetime | None = None,
        enforce_limits: bool = False,
    ) -> SpeechTaskResponse:
        created_at = now or datetime.now(UTC)
        record = SpeechTaskRecord(
            id=self._id_factory(),
            plan_id=plan.id,
            provider_id=plan.provider_id,
            source=source,
            priority=priority,
            created_at=created_at,
            expires_at=expires_at or created_at + timedelta(minutes=5),
        )
        async with self._quota_session() as session:
            if enforce_limits:
                settings = await session.get(DigitalHumanSettingsRecord, 1)
                if not settings.enabled:
                    raise SpeechQuotaRejected("DIGITAL_HUMAN_DISABLED")
                period = self._period(created_at)
                count = await session.scalar(
                    select(func.count(SpeechTaskRecord.id)).where(
                        SpeechTaskRecord.created_at >= period,
                        SpeechTaskRecord.created_at < period + timedelta(days=1),
                    )
                )
                if count >= settings.daily_task_limit:
                    raise SpeechQuotaRejected("SPEECH_DAILY_TASK_LIMIT")
                latest = await session.scalar(
                    select(func.max(SpeechTaskRecord.created_at))
                    .join(SpeechPlanRecord, SpeechPlanRecord.id == SpeechTaskRecord.plan_id)
                    .where(
                        SpeechPlanRecord.screen_id == plan.screen_id,
                        SpeechPlanRecord.component_id == plan.component_id,
                    )
                )
                if (
                    latest is not None
                    and (created_at - latest).total_seconds() < settings.cooldown_seconds
                ):
                    raise SpeechQuotaRejected("SPEECH_COOLDOWN_ACTIVE")
                if await self._audio_used(session, period) >= settings.daily_audio_seconds_limit:
                    raise SpeechQuotaRejected("SPEECH_DAILY_AUDIO_LIMIT")
            session.add(record)
            await session.flush()
        return SpeechTaskResponse.model_validate(record, from_attributes=True)

    async def recoverable_task_ids(self, *, now: datetime | None = None) -> tuple[str, ...]:
        """Expire stale work without touching another live worker or replaying speech."""
        now = now or datetime.now(UTC)
        async with self._quota_session() as session:
            records = tuple(
                await session.scalars(
                    select(SpeechTaskRecord).where(
                        or_(
                            (SpeechTaskRecord.status == "running")
                            & or_(
                                SpeechTaskRecord.lease_expires_at.is_(None),
                                SpeechTaskRecord.lease_expires_at <= now,
                            ),
                            (SpeechTaskRecord.status == "queued")
                            & (SpeechTaskRecord.expires_at <= now),
                        )
                    )
                )
            )
            for record in records:
                record.error_code = (
                    "SPEECH_TASK_EXPIRED"
                    if record.status == "queued"
                    else "SPEECH_TASK_INTERRUPTED"
                )
                record.status = "failed"
                record.finished_at = now
                record.lease_owner = None
                record.lease_expires_at = None
                record.reserved_audio_seconds = 0
                record.quota_period = None
            await session.flush()
            return tuple(record.id for record in records)

    async def get_task(self, task_id: str) -> SpeechTaskResponse:
        async with self._factory() as session:
            record = await session.get(SpeechTaskRecord, task_id)
            if record is None:
                raise SpeechTaskNotFound(task_id)
            return SpeechTaskResponse.model_validate(record, from_attributes=True)

    async def list_tasks(
        self, *, status: str | None = None, limit: int = 50
    ) -> tuple[SpeechTaskResponse, ...]:
        async with self._factory() as session:
            statement = select(SpeechTaskRecord).order_by(
                SpeechTaskRecord.created_at.desc(), SpeechTaskRecord.id
            )
            if status is not None:
                statement = statement.where(SpeechTaskRecord.status == status)
            records = await session.scalars(statement.limit(max(1, min(limit, 100))))
            return tuple(
                SpeechTaskResponse.model_validate(record, from_attributes=True)
                for record in records
            )

    async def queued_task_ids(self, *, limit: int = 20) -> tuple[str, ...]:
        """Return work in dispatch order without changing the admin list order.

        Persistent workers share this query across processes.  Priority is the
        first ordering key and creation time is the FIFO tie-breaker; the task
        id makes the result deterministic when two rows share a timestamp.
        Claiming remains an atomic operation in ``mark_task_running``.
        """
        async with self._factory() as session:
            records = await session.scalars(
                select(SpeechTaskRecord.id)
                .where(SpeechTaskRecord.status == "queued")
                .order_by(
                    SpeechTaskRecord.priority.desc(),
                    SpeechTaskRecord.created_at,
                    SpeechTaskRecord.id,
                )
                .limit(max(1, min(limit, 100)))
            )
            return tuple(records)

    async def playback_diagnostics(
        self,
        *,
        screen_id: str | None = None,
        component_id: str | None = None,
        limit: int = 50,
    ) -> tuple[DigitalHumanPlaybackDiagnosticResponse, ...]:
        async with self._factory() as session:
            statement = (
                select(SpeechTaskRecord, SpeechPlanRecord)
                .join(SpeechPlanRecord, SpeechPlanRecord.id == SpeechTaskRecord.plan_id)
                .order_by(SpeechTaskRecord.created_at.desc(), SpeechTaskRecord.id)
            )
            if screen_id is not None:
                statement = statement.where(SpeechPlanRecord.screen_id == screen_id)
            if component_id is not None:
                statement = statement.where(SpeechPlanRecord.component_id == component_id)
            rows = await session.execute(statement.limit(max(1, min(limit, 100))))
            return tuple(
                DigitalHumanPlaybackDiagnosticResponse(
                    screen_id=plan.screen_id,
                    component_id=plan.component_id,
                    task_id=task.id,
                    status=task.status,
                    provider_id=task.provider_id,
                    source=task.source,
                    asset_id=task.asset_id,
                    error_code=task.error_code,
                    created_at=task.created_at,
                    started_at=task.started_at,
                    finished_at=task.finished_at,
                )
                for task, plan in rows
            )

    async def cached_task(self, plan: SpeechPlanResponse) -> SpeechTaskResponse | None:
        async with self._factory() as session:
            record = await session.scalar(
                select(SpeechTaskRecord)
                .join(SpeechPlanRecord, SpeechPlanRecord.id == SpeechTaskRecord.plan_id)
                .where(
                    SpeechPlanRecord.content_hash == plan.content_hash,
                    SpeechTaskRecord.provider_id == plan.provider_id,
                    SpeechTaskRecord.status == "succeeded",
                    SpeechTaskRecord.asset_id != "",
                )
                .order_by(SpeechTaskRecord.finished_at.desc(), SpeechTaskRecord.id)
                .limit(1)
            )
            if record is None:
                return None
            return SpeechTaskResponse.model_validate(record, from_attributes=True)

    async def detach_cached_tasks(self, provider_id: str | None = None) -> tuple[str, ...]:
        async with self._factory.begin() as session:
            statement = select(SpeechTaskRecord.id, SpeechTaskRecord.asset_id).where(
                SpeechTaskRecord.status == "succeeded",
                SpeechTaskRecord.asset_id != "",
            )
            if provider_id:
                statement = statement.where(SpeechTaskRecord.provider_id == provider_id)
            rows = tuple(
                (task_id, asset_id) for task_id, asset_id in await session.execute(statement)
            )
            if not rows:
                return ()
            task_ids = [task_id for task_id, _ in rows]
            await session.execute(
                update(SpeechTaskRecord)
                .where(SpeechTaskRecord.id.in_(task_ids))
                .values(asset_id="")
            )
            self._audit(
                session,
                action="speech.cache_cleared",
                resource_type="speech_cache",
                resource_id=provider_id or "all",
                details={"detached_tasks": str(len(task_ids))},
            )
            return tuple(asset_id for _, asset_id in rows)

    async def detach_cached_tasks_before(self, cutoff: datetime) -> tuple[str, ...]:
        """Detach cache references older than the retention cutoff.

        The task rows remain available to the normal retention pass so audit and
        usage history keep their existing lifecycle. Returning asset ids lets the
        service remove only files that are no longer referenced by newer tasks.
        """
        async with self._factory.begin() as session:
            statement = select(SpeechTaskRecord.id, SpeechTaskRecord.asset_id).where(
                SpeechTaskRecord.status == "succeeded",
                SpeechTaskRecord.asset_id != "",
                func.coalesce(SpeechTaskRecord.finished_at, SpeechTaskRecord.created_at) < cutoff,
            )
            rows = tuple(
                (task_id, asset_id) for task_id, asset_id in await session.execute(statement)
            )
            if not rows:
                return ()
            await session.execute(
                update(SpeechTaskRecord)
                .where(SpeechTaskRecord.id.in_([task_id for task_id, _ in rows]))
                .values(asset_id="")
            )
            self._audit(
                session,
                action="speech.cache_retention_cleared",
                resource_type="speech_cache",
                resource_id="retention",
                details={"detached_tasks": str(len(rows))},
            )
            return tuple(asset_id for _, asset_id in rows)

    async def cached_asset_references(self, asset_id: str) -> int:
        """Return the number of remaining successful tasks using an asset."""
        async with self._factory() as session:
            return int(
                await session.scalar(
                    select(func.count(SpeechTaskRecord.id)).where(
                        SpeechTaskRecord.status == "succeeded",
                        SpeechTaskRecord.asset_id == asset_id,
                    )
                )
                or 0
            )

    async def mark_task_running(
        self,
        task_id: str,
        started_at: datetime,
        *,
        lease_owner: str | None = None,
        lease_seconds: float = 60,
    ) -> SpeechTaskResponse | None:
        async with self._quota_session() as session:
            claimed = await session.execute(
                update(SpeechTaskRecord)
                .where(
                    SpeechTaskRecord.id == task_id,
                    SpeechTaskRecord.status == "queued",
                    or_(
                        SpeechTaskRecord.expires_at.is_(None),
                        SpeechTaskRecord.expires_at > started_at,
                    ),
                )
                .values(
                    status="running",
                    started_at=started_at,
                    lease_owner=lease_owner or str(uuid4()),
                    lease_expires_at=started_at + timedelta(seconds=lease_seconds),
                )
            )
            record = await session.get(SpeechTaskRecord, task_id)
            if record is None:
                raise SpeechTaskNotFound(task_id)
            if claimed.rowcount:
                return SpeechTaskResponse.model_validate(record, from_attributes=True)
            if (
                record.status == "queued"
                and record.expires_at is not None
                and record.expires_at <= started_at
            ):
                record.status = "failed"
                record.error_code = "SPEECH_TASK_EXPIRED"
                record.finished_at = started_at
                await session.flush()
                return SpeechTaskResponse.model_validate(record, from_attributes=True)
            # Another worker owns a queued-to-running transition. Returning
            # None lets the caller avoid doing duplicate synthesis.
            return None

    async def renew_task_lease(
        self, task_id: str, lease_owner: str, now: datetime, *, lease_seconds: float = 60
    ) -> bool:
        async with self._quota_session() as session:
            result = await session.execute(
                update(SpeechTaskRecord)
                .where(
                    SpeechTaskRecord.id == task_id,
                    SpeechTaskRecord.status == "running",
                    SpeechTaskRecord.lease_owner == lease_owner,
                    SpeechTaskRecord.lease_expires_at > now,
                )
                .values(lease_expires_at=now + timedelta(seconds=lease_seconds))
            )
            return bool(result.rowcount)

    async def reserve_audio(self, task_id: str, lease_owner: str, now: datetime) -> float:
        async with self._quota_session() as session:
            record = await session.get(SpeechTaskRecord, task_id)
            if record is None:
                raise SpeechTaskNotFound(task_id)
            if (
                record.status != "running"
                or record.lease_owner != lease_owner
                or record.lease_expires_at is None
                or record.lease_expires_at <= now
            ):
                raise SpeechQuotaRejected("SPEECH_TASK_LEASE_LOST")
            settings = await session.get(DigitalHumanSettingsRecord, 1)
            period = self._period(now)
            reserved = float(
                await session.scalar(
                    select(func.sum(SpeechTaskRecord.reserved_audio_seconds)).where(
                        SpeechTaskRecord.quota_period == period, SpeechTaskRecord.id != task_id
                    )
                )
                or 0
            )
            available = (
                settings.daily_audio_seconds_limit
                - await self._audio_used(session, period)
                - reserved
            )
            if available <= 0:
                raise SpeechQuotaRejected("SPEECH_DAILY_AUDIO_LIMIT")
            record.reserved_audio_seconds = float(min(settings.max_speech_seconds, available))
            record.quota_period = period
            await session.flush()
            return record.reserved_audio_seconds

    async def _increment_usage(
        self,
        session: AsyncSession,
        provider_id: str,
        period: datetime,
        increments: dict[str, int | float],
    ) -> None:
        record = await session.scalar(
            select(DigitalHumanUsageRecord)
            .where(
                DigitalHumanUsageRecord.period_start == period,
                DigitalHumanUsageRecord.provider_id == provider_id,
            )
            .with_for_update()
        )
        if record is None:
            record = DigitalHumanUsageRecord(
                id=self._id_factory(), period_start=period, provider_id=provider_id
            )
            session.add(record)
            await session.flush()
        for name, value in increments.items():
            setattr(record, name, getattr(record, name) + value)

    async def finish_task(
        self,
        task_id: str,
        *,
        status: str,
        finished_at: datetime,
        asset_id: str = "",
        error_code: str | None = None,
        lease_owner: str | None = None,
        duration_seconds: float = 0,
        estimated_cost: float = 0,
        cache_hit: bool = False,
        account_usage: bool = False,
    ) -> SpeechTaskResponse:
        if status not in {"succeeded", "failed", "cancelled"}:
            raise ValueError("Task completion requires a terminal status.")
        async with self._quota_session() as session:
            record = await session.get(SpeechTaskRecord, task_id)
            if record is None:
                raise SpeechTaskNotFound(task_id)
            if record.status not in {"queued", "running"}:
                return SpeechTaskResponse.model_validate(record, from_attributes=True)
            if lease_owner is not None and (
                record.status != "running"
                or record.lease_owner != lease_owner
                or record.lease_expires_at is None
                or record.lease_expires_at <= finished_at
            ):
                return SpeechTaskResponse.model_validate(record, from_attributes=True)
            period = record.quota_period or self._period(finished_at)
            if status == "succeeded" and account_usage and not cache_hit:
                settings = await session.get(DigitalHumanSettingsRecord, 1)
                if duration_seconds < 0 or duration_seconds > settings.max_speech_seconds:
                    raise SpeechQuotaRejected("SPEECH_MAX_DURATION_EXCEEDED")
                if duration_seconds > record.reserved_audio_seconds or (
                    await self._audio_used(session, period) + duration_seconds
                    > settings.daily_audio_seconds_limit
                ):
                    raise SpeechQuotaRejected("SPEECH_DAILY_AUDIO_LIMIT")
            record.status = status
            record.asset_id = asset_id
            record.error_code = error_code
            record.finished_at = finished_at
            record.lease_owner = None
            record.lease_expires_at = None
            record.reserved_audio_seconds = 0
            record.quota_period = None
            if account_usage:
                await self._increment_usage(
                    session,
                    record.provider_id,
                    period,
                    {
                        "task_count": 1,
                        "succeeded_count": int(status == "succeeded"),
                        "failed_count": int(status == "failed"),
                        "generated_seconds": duration_seconds if status == "succeeded" else 0,
                        "estimated_cost": estimated_cost if status == "succeeded" else 0,
                        "cached_count": int(cache_hit and status == "succeeded"),
                    },
                )
            if status == "failed":
                self._audit(
                    session,
                    action="speech.failed",
                    resource_type="task",
                    resource_id=task_id,
                    details={"error_code": error_code or "SPEECH_TASK_FAILED"},
                )
            await session.flush()
            return SpeechTaskResponse.model_validate(record, from_attributes=True)

    async def cancel_task(self, task_id: str, finished_at: datetime) -> SpeechTaskResponse:
        return await self.finish_task(
            task_id, status="cancelled", finished_at=finished_at, error_code="SPEECH_TASK_CANCELLED"
        )

    async def record_usage(
        self,
        *,
        provider_id: str,
        task_count: int = 0,
        succeeded_count: int = 0,
        failed_count: int = 0,
        generated_seconds: float = 0,
        cached_count: int = 0,
        estimated_cost: float = 0,
        synthesis_attempts: int = 0,
        synthesis_failures: int = 0,
        synthesis_total_ms: float = 0,
        now: datetime | None = None,
    ) -> None:
        period = (
            (now or datetime.now(UTC))
            .astimezone(UTC)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )
        increments = {
            "task_count": task_count,
            "succeeded_count": succeeded_count,
            "failed_count": failed_count,
            "generated_seconds": generated_seconds,
            "cached_count": cached_count,
            "estimated_cost": estimated_cost,
            "synthesis_attempts": synthesis_attempts,
            "synthesis_failures": synthesis_failures,
            "synthesis_total_ms": synthesis_total_ms,
        }
        async with self._quota_session() as session:
            await self._increment_usage(session, provider_id, period, increments)

    async def record_provider_health(
        self,
        provider_id: str,
        *,
        checked_at: datetime,
        ok: bool,
        latency_ms: int,
        error_code: str | None,
        failure_threshold: int = 3,
        circuit_seconds: int = 60,
    ) -> DigitalHumanProviderResponse:
        async with self._factory.begin() as session:
            record = await session.get(DigitalHumanProviderRecord, provider_id)
            if record is None:
                raise SpeechProviderNotFound(provider_id)
            record.last_checked_at = checked_at
            record.last_latency_ms = max(0, latency_ms)
            record.last_error_code = error_code
            if ok:
                record.consecutive_failures = 0
                record.circuit_open_until = None
            else:
                record.consecutive_failures += 1
                if record.consecutive_failures >= failure_threshold:
                    from datetime import timedelta

                    record.circuit_open_until = checked_at + timedelta(seconds=circuit_seconds)
            if not ok:
                self._audit(
                    session,
                    action="provider.health_failed",
                    resource_type="provider",
                    resource_id=provider_id,
                    details={"error_code": error_code or "SPEECH_PROVIDER_UNAVAILABLE"},
                )
            session.add(
                DigitalHumanProviderHealthRecord(
                    id=self._id_factory(),
                    provider_id=provider_id,
                    checked_at=checked_at,
                    ok=ok,
                    latency_ms=max(0, latency_ms),
                    error_code=error_code,
                )
            )
            await session.flush()
            return self._provider(record, now=checked_at)

    async def provider_health(
        self, provider_id: str, *, limit: int = 50
    ) -> tuple[DigitalHumanProviderHealthResponse, ...]:
        async with self._factory() as session:
            records = await session.scalars(
                select(DigitalHumanProviderHealthRecord)
                .where(DigitalHumanProviderHealthRecord.provider_id == provider_id)
                .order_by(
                    DigitalHumanProviderHealthRecord.checked_at.desc(),
                    DigitalHumanProviderHealthRecord.id,
                )
                .limit(max(1, min(limit, 200)))
            )
            return tuple(
                DigitalHumanProviderHealthResponse.model_validate(record, from_attributes=True)
                for record in records
            )

    async def task_count_since(self, period_start: datetime) -> int:
        async with self._factory() as session:
            return int(
                await session.scalar(
                    select(func.count(SpeechTaskRecord.id)).where(
                        SpeechTaskRecord.created_at >= period_start
                    )
                )
                or 0
            )

    async def latest_task_at(self, screen_id: str, component_id: str) -> datetime | None:
        async with self._factory() as session:
            return await session.scalar(
                select(SpeechTaskRecord.created_at)
                .join(SpeechPlanRecord, SpeechPlanRecord.id == SpeechTaskRecord.plan_id)
                .where(
                    SpeechPlanRecord.screen_id == screen_id,
                    SpeechPlanRecord.component_id == component_id,
                )
                .order_by(SpeechTaskRecord.created_at.desc())
                .limit(1)
            )

    async def get_plan(self, plan_id: str) -> SpeechPlanResponse:
        async with self._factory() as session:
            record = await session.get(SpeechPlanRecord, plan_id)
            if record is None:
                raise SpeechProviderNotFound(plan_id)
            return SpeechPlanResponse.model_validate(record, from_attributes=True)

    async def usage(self) -> DigitalHumanUsageResponse:
        period = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        async with self._factory() as session:
            records = tuple(
                await session.scalars(
                    select(DigitalHumanUsageRecord).where(
                        DigitalHumanUsageRecord.period_start == period
                    )
                )
            )
        return DigitalHumanUsageResponse(
            period_start=period,
            task_count=sum(item.task_count for item in records),
            succeeded_count=sum(item.succeeded_count for item in records),
            failed_count=sum(item.failed_count for item in records),
            generated_seconds=sum(item.generated_seconds for item in records),
            cached_count=sum(item.cached_count for item in records),
            estimated_cost=sum(item.estimated_cost for item in records),
        )

    async def metrics_snapshot(self, now: datetime) -> dict[str, int | float]:
        """Aggregate low-cardinality task metrics across all worker processes."""
        period = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        async with self._factory() as session:
            task_rows = await session.execute(
                select(SpeechTaskRecord.status, func.count(SpeechTaskRecord.id))
                .where(
                    SpeechTaskRecord.created_at >= period,
                    SpeechTaskRecord.created_at < period + timedelta(days=1),
                )
                .group_by(SpeechTaskRecord.status)
            )
            usage_row = await session.execute(
                select(
                    func.coalesce(func.sum(DigitalHumanUsageRecord.cached_count), 0),
                    func.coalesce(func.sum(DigitalHumanUsageRecord.synthesis_attempts), 0),
                    func.coalesce(func.sum(DigitalHumanUsageRecord.synthesis_failures), 0),
                    func.coalesce(func.sum(DigitalHumanUsageRecord.synthesis_total_ms), 0),
                ).where(DigitalHumanUsageRecord.period_start == period)
            )
        counts = {status: int(count) for status, count in task_rows}
        (
            cached_count,
            synthesis_attempts,
            synthesis_failures,
            synthesis_total_ms,
        ) = tuple(usage_row.one())
        cached = int(cached_count or 0)
        return {
            "tasks_queued": counts.get("queued", 0),
            "tasks_succeeded": counts.get("succeeded", 0),
            "tasks_failed": counts.get("failed", 0),
            "tasks_cancelled": counts.get("cancelled", 0),
            "cache_hits": cached,
            "synthesis_attempts": int(synthesis_attempts or 0),
            "synthesis_failures": int(synthesis_failures or 0),
            "synthesis_total_ms": float(synthesis_total_ms or 0),
        }

    async def cost_report(
        self, *, period_start: datetime, period_end: datetime
    ) -> DigitalHumanCostReportResponse:
        async with self._factory() as session:
            rows = await session.execute(
                select(DigitalHumanUsageRecord, DigitalHumanProviderRecord.name)
                .join(
                    DigitalHumanProviderRecord,
                    DigitalHumanProviderRecord.id == DigitalHumanUsageRecord.provider_id,
                    isouter=True,
                )
                .where(
                    DigitalHumanUsageRecord.period_start >= period_start,
                    DigitalHumanUsageRecord.period_start < period_end,
                )
                .order_by(DigitalHumanUsageRecord.period_start, DigitalHumanUsageRecord.provider_id)
            )
            report_rows = tuple(
                DigitalHumanCostReportRow(
                    provider_id=record.provider_id,
                    provider_name=name or record.provider_id,
                    task_count=record.task_count,
                    succeeded_count=record.succeeded_count,
                    failed_count=record.failed_count,
                    cached_count=record.cached_count,
                    generated_seconds=record.generated_seconds,
                    estimated_cost=record.estimated_cost,
                )
                for record, name in rows
            )
        return DigitalHumanCostReportResponse(
            period_start=period_start,
            period_end=period_end,
            rows=report_rows,
            total_task_count=sum(row.task_count for row in report_rows),
            total_generated_seconds=sum(row.generated_seconds for row in report_rows),
            total_estimated_cost=sum(row.estimated_cost for row in report_rows),
        )

    async def prune_speech_data(self, cutoff: datetime) -> int:
        async with self._factory.begin() as session:
            deleted = 0
            for model, field in (
                (DigitalHumanProviderHealthRecord, DigitalHumanProviderHealthRecord.checked_at),
                (DigitalHumanUsageRecord, DigitalHumanUsageRecord.period_start),
                (SpeechTaskRecord, SpeechTaskRecord.created_at),
                (SpeechPlanRecord, SpeechPlanRecord.created_at),
                (DigitalHumanAuditRecord, DigitalHumanAuditRecord.created_at),
            ):
                result = await session.execute(delete(model).where(field < cutoff))
                deleted += result.rowcount or 0
            return deleted

    async def list_audit(self, *, limit: int = 100) -> tuple[DigitalHumanAuditResponse, ...]:
        async with self._factory() as session:
            records = await session.scalars(
                select(DigitalHumanAuditRecord)
                .order_by(DigitalHumanAuditRecord.created_at.desc(), DigitalHumanAuditRecord.id)
                .limit(max(1, min(limit, 500)))
            )
            return tuple(
                DigitalHumanAuditResponse(
                    id=record.id,
                    created_at=record.created_at,
                    actor=record.actor,
                    action=record.action,
                    resource_type=record.resource_type,
                    resource_id=record.resource_id,
                    request_id=record.request_id,
                    details=record.details_json,
                )
                for record in records
            )

    async def record_audit_event(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict[str, str] | None = None,
    ) -> None:
        async with self._factory.begin() as session:
            self._audit(
                session,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
            )
