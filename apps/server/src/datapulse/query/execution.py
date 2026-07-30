import asyncio
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from datapulse.datasource.connector import (
    Connector,
    ConnectorSecret,
    QueryPolicy,
    QueryStream,
)
from datapulse.datasource.models import DatasourceConfig
from datapulse.metadata import QueryRunRecord, QueryRunStatus
from datapulse.query.limits import QueryConcurrencyLimited, QueryLimiter
from datapulse.query.models import QueryColumn, QueryRequest, QueryResult
from datapulse.query.normalization import normalize_result_value
from datapulse.query.parameters import validate_parameters
from datapulse.query.safety import validate_read_only_sql


class QueryExecutionError(RuntimeError):
    def __init__(self, code: str, status_code: int, request_id: str) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.request_id = request_id


class QueryRunRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(
        self,
        *,
        request_id: str,
        datasource_id: str,
        dataset_id: str | None,
        trigger: str,
        query_hash: str,
        started_at: datetime,
    ) -> None:
        async with self._session_factory.begin() as session:
            session.add(
                QueryRunRecord(
                    id=request_id,
                    data_source_id=datasource_id,
                    dataset_id=dataset_id,
                    trigger=trigger,
                    query_hash=query_hash,
                    status=QueryRunStatus.RUNNING.value,
                    started_at=started_at,
                )
            )

    async def finalize(
        self,
        request_id: str,
        *,
        status: QueryRunStatus,
        duration_ms: int,
        row_count: int | None,
        truncated: bool | None,
        error_code: str | None,
        finished_at: datetime,
    ) -> None:
        async with self._session_factory.begin() as session:
            await session.execute(
                update(QueryRunRecord)
                .where(QueryRunRecord.id == request_id)
                .values(
                    status=status.value,
                    duration_ms=duration_ms,
                    row_count=row_count,
                    truncated=truncated,
                    error_code=error_code,
                    finished_at=finished_at,
                )
            )

    async def get(self, request_id: str) -> QueryRunRecord:
        async with self._session_factory() as session:
            record = await session.get(QueryRunRecord, request_id)
        if record is None:
            raise LookupError(request_id)
        return record

    async def list(self) -> tuple[QueryRunRecord, ...]:
        async with self._session_factory() as session:
            records = (
                await session.scalars(select(QueryRunRecord).order_by(QueryRunRecord.started_at))
            ).all()
        return tuple(records)


class QueryExecutor:
    def __init__(
        self,
        *,
        repository: QueryRunRepository,
        limiter: QueryLimiter,
        clock: Callable[[], datetime] | None = None,
        request_id_factory: Callable[[], str],
    ) -> None:
        self._repository = repository
        self._limiter = limiter
        self._clock = clock or (lambda: datetime.now(UTC))
        self._request_id_factory = request_id_factory

    def _duration_ms(self, started_at: datetime) -> int:
        return max(0, round((self._clock() - started_at).total_seconds() * 1000))

    async def _finalize(
        self,
        request_id: str,
        started_at: datetime,
        *,
        status: QueryRunStatus,
        row_count: int | None = None,
        truncated: bool | None = None,
        error_code: str | None = None,
    ) -> None:
        finished_at = self._clock()
        await self._repository.finalize(
            request_id,
            status=status,
            duration_ms=max(
                0,
                round((finished_at - started_at).total_seconds() * 1000),
            ),
            row_count=row_count,
            truncated=truncated,
            error_code=error_code,
            finished_at=finished_at,
        )

    async def execute(
        self,
        *,
        datasource_id: str,
        dataset_id: str | None,
        trigger: str,
        connector: Connector,
        config: DatasourceConfig,
        secret: ConnectorSecret | None,
        request: QueryRequest,
        request_id: str | None = None,
    ) -> QueryResult:
        validated = validate_read_only_sql(request.sql, connector.dialect)
        validate_parameters(validated, request.parameters)
        request_id = request_id or self._request_id_factory()
        started_at = self._clock()
        await self._repository.create(
            request_id=request_id,
            datasource_id=datasource_id,
            dataset_id=dataset_id,
            trigger=trigger,
            query_hash=validated.query_hash,
            started_at=started_at,
        )

        stream: QueryStream | None = None
        try:
            async with self._limiter.acquire(datasource_id):
                async with asyncio.timeout(request.timeout_seconds):
                    stream = await connector.stream_query(
                        config,
                        secret,
                        validated,
                        request.parameters,
                        QueryPolicy.model_construct(
                            timeout_seconds=request.timeout_seconds,
                            max_rows=request.max_rows,
                        ),
                    )
                    rows: list[tuple[object, ...]] = []
                    truncated = False
                    async for raw_row in stream:
                        if len(rows) >= request.max_rows:
                            truncated = True
                            break
                        rows.append(tuple(normalize_result_value(value) for value in raw_row))
            await self._finalize(
                request_id,
                started_at,
                status=QueryRunStatus.SUCCEEDED,
                row_count=len(rows),
                truncated=truncated,
            )
            return QueryResult(
                request_id=request_id,
                columns=tuple(
                    QueryColumn(name=column.name, data_type=column.data_type)
                    for column in stream.columns
                ),
                rows=tuple(rows),
                row_count=len(rows),
                truncated=truncated,
                duration_ms=self._duration_ms(started_at),
            )
        except asyncio.CancelledError:
            await self._finalize(
                request_id,
                started_at,
                status=QueryRunStatus.CANCELLED,
                error_code="QUERY_CANCELLED",
            )
            raise
        except TimeoutError as error:
            await self._finalize(
                request_id,
                started_at,
                status=QueryRunStatus.TIMED_OUT,
                error_code="QUERY_TIMEOUT",
            )
            raise QueryExecutionError("QUERY_TIMEOUT", 504, request_id) from error
        except QueryConcurrencyLimited as error:
            await self._finalize(
                request_id,
                started_at,
                status=QueryRunStatus.FAILED,
                error_code="QUERY_CONCURRENCY_LIMITED",
            )
            raise QueryExecutionError(
                "QUERY_CONCURRENCY_LIMITED",
                429,
                request_id,
            ) from error
        except Exception as error:
            await self._finalize(
                request_id,
                started_at,
                status=QueryRunStatus.FAILED,
                error_code="QUERY_EXECUTION_FAILED",
            )
            raise QueryExecutionError(
                "QUERY_EXECUTION_FAILED",
                502,
                request_id,
            ) from error
        finally:
            if stream is not None:
                await asyncio.shield(stream.aclose())
