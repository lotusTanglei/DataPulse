import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class QueryConcurrencyLimited(RuntimeError):
    pass


class QueryLimiter:
    def __init__(
        self,
        *,
        global_limit: int,
        per_source_limit: int,
        acquire_timeout: float,
    ) -> None:
        if global_limit < 1 or per_source_limit < 1 or acquire_timeout < 0:
            raise ValueError("Query limits must be positive.")
        self._global_limit = global_limit
        self._per_source_limit = per_source_limit
        self._acquire_timeout = acquire_timeout
        self._global_active = 0
        self._source_active: defaultdict[str, int] = defaultdict(int)
        self._condition = asyncio.Condition()

    def _available(self, datasource_id: str) -> bool:
        return (
            self._global_active < self._global_limit
            and self._source_active[datasource_id] < self._per_source_limit
        )

    async def _reserve(self, datasource_id: str) -> None:
        if self._acquire_timeout == 0:
            async with self._condition:
                if not self._available(datasource_id):
                    raise QueryConcurrencyLimited
                self._global_active += 1
                self._source_active[datasource_id] += 1
            return
        try:
            async with asyncio.timeout(self._acquire_timeout):
                async with self._condition:
                    await self._condition.wait_for(lambda: self._available(datasource_id))
                    self._global_active += 1
                    self._source_active[datasource_id] += 1
        except TimeoutError as error:
            raise QueryConcurrencyLimited from error

    async def _release(self, datasource_id: str) -> None:
        async with self._condition:
            self._global_active -= 1
            self._source_active[datasource_id] -= 1
            if self._source_active[datasource_id] == 0:
                del self._source_active[datasource_id]
            self._condition.notify_all()

    @asynccontextmanager
    async def acquire(self, datasource_id: str) -> AsyncIterator[None]:
        await self._reserve(datasource_id)
        try:
            yield
        finally:
            await self._release(datasource_id)
