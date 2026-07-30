from datetime import datetime

from pydantic import TypeAdapter
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from datapulse.datasource.models import (
    DatasourceConfig,
    DatasourceCreate,
    DatasourceResponse,
    DatasourceStatus,
    DatasourceUpdate,
)
from datapulse.datasource.secrets import SecretEnvelope
from datapulse.metadata import DataSourceRecord
from datapulse.metadata.models import utc_now


class DatasourceNotFound(LookupError):
    pass


class DatasourceNameConflict(ValueError):
    pass


class DatasourceInUse(ValueError):
    pass


class _Unset:
    pass


UNSET = _Unset()
type SecretPatch = SecretEnvelope | None | _Unset
_config_adapter = TypeAdapter(DatasourceConfig)


class DatasourceRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _to_response(record: DataSourceRecord) -> DatasourceResponse:
        return DatasourceResponse(
            id=record.id,
            name=record.name,
            config=_config_adapter.validate_python(record.config_json),
            status=DatasourceStatus(record.status),
            has_password=record.secret_envelope is not None,
            last_checked_at=record.last_checked_at,
            last_latency_ms=record.last_latency_ms,
            last_error_code=record.last_error_code,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    async def create(
        self,
        datasource_id: str,
        data: DatasourceCreate,
        *,
        secret_envelope: SecretEnvelope | None = None,
    ) -> DatasourceResponse:
        record = DataSourceRecord(
            id=datasource_id,
            name=data.name,
            connector_type=data.config.type.value,
            config_json=data.config.model_dump(mode="json"),
            secret_envelope=(
                secret_envelope.model_dump_json() if secret_envelope is not None else None
            ),
        )
        try:
            async with self._session_factory.begin() as session:
                session.add(record)
                await session.flush()
        except IntegrityError as error:
            raise DatasourceNameConflict(data.name) from error
        return self._to_response(record)

    async def list(self) -> tuple[DatasourceResponse, ...]:
        async with self._session_factory() as session:
            records = (
                await session.scalars(
                    select(DataSourceRecord).order_by(
                        DataSourceRecord.created_at,
                        DataSourceRecord.name,
                    )
                )
            ).all()
        return tuple(self._to_response(record) for record in records)

    async def get(self, datasource_id: str) -> DatasourceResponse:
        async with self._session_factory() as session:
            record = await session.get(DataSourceRecord, datasource_id)
        if record is None:
            raise DatasourceNotFound(datasource_id)
        return self._to_response(record)

    async def get_secret_envelope(self, datasource_id: str) -> SecretEnvelope | None:
        async with self._session_factory() as session:
            value = await session.scalar(
                select(DataSourceRecord.secret_envelope).where(DataSourceRecord.id == datasource_id)
            )
            exists = await session.scalar(
                select(DataSourceRecord.id).where(DataSourceRecord.id == datasource_id)
            )
        if exists is None:
            raise DatasourceNotFound(datasource_id)
        return SecretEnvelope.model_validate_json(value) if value is not None else None

    async def update(
        self,
        datasource_id: str,
        data: DatasourceUpdate,
        *,
        secret_envelope: SecretPatch = UNSET,
    ) -> DatasourceResponse:
        if data.password is not None and isinstance(secret_envelope, _Unset):
            raise ValueError("An encrypted secret envelope is required.")
        try:
            async with self._session_factory.begin() as session:
                record = await session.get(DataSourceRecord, datasource_id)
                if record is None:
                    raise DatasourceNotFound(datasource_id)
                if data.name is not None:
                    record.name = data.name
                if data.config is not None:
                    record.connector_type = data.config.type.value
                    record.config_json = data.config.model_dump(mode="json")
                if data.clear_password:
                    record.secret_envelope = None
                elif not isinstance(secret_envelope, _Unset):
                    record.secret_envelope = (
                        secret_envelope.model_dump_json() if secret_envelope is not None else None
                    )
                record.updated_at = utc_now()
                await session.flush()
        except IntegrityError as error:
            raise DatasourceNameConflict(data.name or "") from error
        return self._to_response(record)

    async def delete(self, datasource_id: str) -> None:
        try:
            async with self._session_factory.begin() as session:
                result = await session.execute(
                    delete(DataSourceRecord).where(DataSourceRecord.id == datasource_id)
                )
                if not result.rowcount:
                    raise DatasourceNotFound(datasource_id)
        except IntegrityError as error:
            raise DatasourceInUse(datasource_id) from error

    async def update_connection_status(
        self,
        datasource_id: str,
        *,
        status: DatasourceStatus,
        checked_at: datetime,
        latency_ms: int,
        error_code: str | None,
    ) -> DatasourceResponse:
        async with self._session_factory.begin() as session:
            record = await session.get(DataSourceRecord, datasource_id)
            if record is None:
                raise DatasourceNotFound(datasource_id)
            record.status = status.value
            record.last_checked_at = checked_at
            record.last_latency_ms = latency_ms
            record.last_error_code = error_code
            await session.flush()
        return self._to_response(record)
