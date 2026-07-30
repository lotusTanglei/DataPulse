from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncResult,
    AsyncTransaction,
)

from datapulse.datasource.connector import StreamColumn


class SQLAlchemyQueryStream:
    def __init__(
        self,
        *,
        columns: tuple[StreamColumn, ...],
        result: AsyncResult[tuple[object, ...]],
        transaction: AsyncTransaction,
        connection: AsyncConnection,
        engine: AsyncEngine,
    ) -> None:
        self.columns = columns
        self._result = result
        self._transaction = transaction
        self._connection = connection
        self._engine = engine
        self._closed = False

    def __aiter__(self) -> AsyncIterator[tuple[object, ...]]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[tuple[object, ...]]:
        async for row in self._result:
            yield tuple(row)

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            await self._result.close()
        finally:
            try:
                if self._transaction.is_active:
                    await self._transaction.rollback()
            finally:
                try:
                    await self._connection.close()
                finally:
                    await self._engine.dispose()
