import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Protocol


class DisposableEngine(Protocol):
    async def dispose(self) -> None: ...


class EngineManager:
    def __init__(self) -> None:
        self._engines: dict[str, tuple[datetime, DisposableEngine]] = {}
        self._lock = asyncio.Lock()

    async def get(
        self,
        datasource_id: str,
        updated_at: datetime,
        factory: Callable[[], DisposableEngine],
    ) -> DisposableEngine:
        async with self._lock:
            cached = self._engines.get(datasource_id)
            if cached is not None and cached[0] == updated_at:
                return cached[1]
            if cached is not None:
                await cached[1].dispose()
            engine = factory()
            self._engines[datasource_id] = (updated_at, engine)
            return engine

    async def dispose(self, datasource_id: str) -> None:
        async with self._lock:
            cached = self._engines.pop(datasource_id, None)
            if cached is not None:
                await cached[1].dispose()

    async def dispose_all(self) -> None:
        async with self._lock:
            engines = tuple(cached[1] for cached in self._engines.values())
            self._engines.clear()
            for engine in engines:
                await engine.dispose()
