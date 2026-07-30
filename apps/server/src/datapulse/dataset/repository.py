import json

from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from datapulse.contracts.dataset import DatasetDefinition
from datapulse.dataset.models import DatasetResponse
from datapulse.metadata import DatasetRecord
from datapulse.metadata.models import utc_now


class DatasetNotFound(LookupError):
    pass


class DatasetNameConflict(ValueError):
    pass


class DatasetSourceNotFound(ValueError):
    pass


class DatasetDefinitionInvalid(ValueError):
    code = "DATASET_DEFINITION_INVALID"


def _canonical_definition(definition: DatasetDefinition) -> dict[str, object]:
    serialized = json.dumps(
        definition.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return json.loads(serialized)


def _is_foreign_key_error(error: IntegrityError) -> bool:
    message = str(error.orig).lower()
    constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", "")
    return "foreign key" in message or "data_source_id" in str(constraint_name)


class DatasetRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _to_response(record: DatasetRecord) -> DatasetResponse:
        try:
            definition = DatasetDefinition.model_validate(record.definition_json)
            if (
                definition.id != record.id
                or definition.name != record.name
                or definition.data_source_id != record.data_source_id
            ):
                raise ValueError("Dataset indexed fields do not match its definition.")
        except (TypeError, ValueError, ValidationError) as error:
            raise DatasetDefinitionInvalid(record.id) from error
        return DatasetResponse(
            id=record.id,
            name=record.name,
            data_source_id=record.data_source_id,
            definition=definition,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    async def create(self, definition: DatasetDefinition) -> DatasetResponse:
        if definition.data_source_id is None:
            raise DatasetSourceNotFound("")
        record = DatasetRecord(
            id=definition.id,
            name=definition.name,
            data_source_id=definition.data_source_id,
            definition_json=_canonical_definition(definition),
        )
        try:
            async with self._session_factory.begin() as session:
                session.add(record)
                await session.flush()
        except IntegrityError as error:
            if _is_foreign_key_error(error):
                raise DatasetSourceNotFound(definition.data_source_id) from error
            raise DatasetNameConflict(definition.name) from error
        return self._to_response(record)

    async def list(self) -> tuple[DatasetResponse, ...]:
        async with self._session_factory() as session:
            records = (
                await session.scalars(
                    select(DatasetRecord).order_by(
                        DatasetRecord.created_at,
                        DatasetRecord.name,
                    )
                )
            ).all()
        return tuple(self._to_response(record) for record in records)

    async def get(self, dataset_id: str) -> DatasetResponse:
        async with self._session_factory() as session:
            record = await session.get(DatasetRecord, dataset_id)
        if record is None:
            raise DatasetNotFound(dataset_id)
        return self._to_response(record)

    async def update(
        self,
        dataset_id: str,
        definition: DatasetDefinition,
    ) -> DatasetResponse:
        if definition.id != dataset_id:
            raise DatasetDefinitionInvalid(dataset_id)
        if definition.data_source_id is None:
            raise DatasetSourceNotFound("")
        try:
            async with self._session_factory.begin() as session:
                record = await session.get(DatasetRecord, dataset_id)
                if record is None:
                    raise DatasetNotFound(dataset_id)
                record.name = definition.name
                record.data_source_id = definition.data_source_id
                record.definition_json = _canonical_definition(definition)
                record.updated_at = utc_now()
                await session.flush()
        except IntegrityError as error:
            if _is_foreign_key_error(error):
                raise DatasetSourceNotFound(definition.data_source_id) from error
            raise DatasetNameConflict(definition.name) from error
        return self._to_response(record)

    async def delete(self, dataset_id: str) -> None:
        async with self._session_factory.begin() as session:
            result = await session.execute(
                delete(DatasetRecord).where(DatasetRecord.id == dataset_id)
            )
            if not result.rowcount:
                raise DatasetNotFound(dataset_id)
