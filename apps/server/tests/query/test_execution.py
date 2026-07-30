import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest

from datapulse.datasource.connector import QueryPolicy, StreamColumn
from datapulse.datasource.models import ConnectorType, SQLiteConfig
from datapulse.query.execution import (
    QueryExecutionError,
    QueryExecutor,
    QueryRunRepository,
)
from datapulse.query.limits import QueryLimiter
from datapulse.query.models import QueryRequest
from datapulse.query.parameters import ParameterValidationError
from datapulse.query.safety import QueryValidationError

pytestmark = pytest.mark.anyio


class FakeStream:
    def __init__(
        self,
        rows: tuple[tuple[object, ...], ...],
        *,
        delay: float = 0,
        error: Exception | None = None,
        entered: asyncio.Event | None = None,
    ) -> None:
        self.columns = (
            StreamColumn(name="month", data_type="string"),
            StreamColumn(name="amount", data_type="decimal"),
        )
        self._rows = rows
        self._delay = delay
        self._error = error
        self._entered = entered
        self.consumed = 0
        self.closed = False

    def __aiter__(self) -> AsyncIterator[tuple[object, ...]]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[tuple[object, ...]]:
        if self._entered is not None:
            self._entered.set()
        for row in self._rows:
            if self._delay:
                await asyncio.sleep(self._delay)
            if self._error is not None:
                raise self._error
            self.consumed += 1
            yield row

    async def aclose(self) -> None:
        self.closed = True


@dataclass
class FakeConnector:
    stream: FakeStream
    type: ConnectorType = ConnectorType.SQLITE
    dialect: str = "sqlite"
    invocations: int = 0

    async def stream_query(
        self,
        config: object,
        secret: object,
        query: object,
        parameters: dict[str, object],
        policy: QueryPolicy,
    ) -> FakeStream:
        del config, secret, query, parameters, policy
        self.invocations += 1
        return self.stream


def build_executor(
    repository: QueryRunRepository,
    *,
    global_limit: int = 4,
    per_source_limit: int = 2,
) -> QueryExecutor:
    return QueryExecutor(
        repository=repository,
        limiter=QueryLimiter(
            global_limit=global_limit,
            per_source_limit=per_source_limit,
            acquire_timeout=0,
        ),
        request_id_factory=lambda: "query-run-1",
    )


async def test_sql_and_parameters_are_validated_before_connector_invocation(
    query_run_repository: QueryRunRepository,
) -> None:
    connector = FakeConnector(FakeStream(()))
    executor = build_executor(query_run_repository)

    with pytest.raises(QueryValidationError):
        await executor.execute(
            datasource_id="source-1",
            dataset_id=None,
            trigger="debug",
            connector=connector,
            config=SQLiteConfig(path="sales.db"),
            secret=None,
            request=QueryRequest(sql="DELETE FROM sales"),
        )
    with pytest.raises(ParameterValidationError):
        await executor.execute(
            datasource_id="source-1",
            dataset_id=None,
            trigger="debug",
            connector=connector,
            config=SQLiteConfig(path="sales.db"),
            secret=None,
            request=QueryRequest(
                sql="SELECT * FROM sales WHERE region = :region",
                parameters={},
            ),
        )

    assert connector.invocations == 0
    assert await query_run_repository.list() == ()


async def test_success_consumes_max_rows_plus_one_and_finalizes_run(
    query_run_repository: QueryRunRepository,
) -> None:
    stream = FakeStream(
        (
            ("2026-01", 100),
            ("2026-02", 200),
            ("2026-03", 300),
            ("2026-04", 400),
        )
    )
    connector = FakeConnector(stream)
    executor = build_executor(query_run_repository)

    result = await executor.execute(
        datasource_id="source-1",
        dataset_id=None,
        trigger="debug",
        connector=connector,
        config=SQLiteConfig(path="sales.db"),
        secret=None,
        request=QueryRequest(sql="SELECT month, amount FROM sales", max_rows=2),
    )
    run = await query_run_repository.get("query-run-1")

    assert result.request_id == "query-run-1"
    assert result.rows == (("2026-01", 100), ("2026-02", 200))
    assert result.row_count == 2
    assert result.truncated is True
    assert stream.consumed == 3
    assert stream.closed is True
    assert run.status == "succeeded"
    assert run.row_count == 2
    assert run.truncated is True
    assert len(run.query_hash) == 64


async def test_timeout_finalizes_run_and_returns_504(
    query_run_repository: QueryRunRepository,
) -> None:
    stream = FakeStream((("2026-01", 100),), delay=1)
    connector = FakeConnector(stream)
    executor = build_executor(query_run_repository)
    request = QueryRequest.model_construct(
        sql="SELECT month, amount FROM sales",
        parameters={},
        max_rows=1000,
        timeout_seconds=0.01,
    )

    with pytest.raises(QueryExecutionError) as captured:
        await executor.execute(
            datasource_id="source-1",
            dataset_id=None,
            trigger="debug",
            connector=connector,
            config=SQLiteConfig(path="sales.db"),
            secret=None,
            request=request,
        )

    run = await query_run_repository.get("query-run-1")
    assert captured.value.status_code == 504
    assert captured.value.code == "QUERY_TIMEOUT"
    assert run.status == "timed_out"
    assert stream.closed is True


async def test_failure_and_cancellation_always_finalize_run(
    query_run_repository: QueryRunRepository,
) -> None:
    failing = FakeStream((("2026-01", 100),), error=RuntimeError("database failed"))
    executor = build_executor(query_run_repository)

    with pytest.raises(QueryExecutionError):
        await executor.execute(
            datasource_id="source-1",
            dataset_id=None,
            trigger="debug",
            connector=FakeConnector(failing),
            config=SQLiteConfig(path="sales.db"),
            secret=None,
            request=QueryRequest(sql="SELECT month, amount FROM sales"),
        )
    assert (await query_run_repository.get("query-run-1")).status == "failed"
    assert failing.closed is True

    entered = asyncio.Event()
    blocking = FakeStream((("2026-01", 100),), delay=60, entered=entered)
    cancelling_executor = QueryExecutor(
        repository=query_run_repository,
        limiter=QueryLimiter(global_limit=1, per_source_limit=1, acquire_timeout=0),
        request_id_factory=lambda: "query-run-2",
    )
    task = asyncio.create_task(
        cancelling_executor.execute(
            datasource_id="source-1",
            dataset_id=None,
            trigger="debug",
            connector=FakeConnector(blocking),
            config=SQLiteConfig(path="sales.db"),
            secret=None,
            request=QueryRequest(sql="SELECT month, amount FROM sales"),
        )
    )
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert (await query_run_repository.get("query-run-2")).status == "cancelled"
    assert blocking.closed is True
