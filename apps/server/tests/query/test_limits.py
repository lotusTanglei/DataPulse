import asyncio
from contextlib import AsyncExitStack

import pytest

from datapulse.query.limits import QueryConcurrencyLimited, QueryLimiter

pytestmark = pytest.mark.anyio


async def test_third_query_for_one_source_is_rejected_immediately() -> None:
    limiter = QueryLimiter(global_limit=4, per_source_limit=2, acquire_timeout=0)
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(limiter.acquire("source-a"))
        await stack.enter_async_context(limiter.acquire("source-a"))

        with pytest.raises(QueryConcurrencyLimited):
            async with limiter.acquire("source-a"):
                pass


async def test_fifth_global_query_is_rejected_immediately() -> None:
    limiter = QueryLimiter(global_limit=4, per_source_limit=2, acquire_timeout=0)
    async with AsyncExitStack() as stack:
        for source_id in ("source-a", "source-b", "source-c", "source-d"):
            await stack.enter_async_context(limiter.acquire(source_id))

        with pytest.raises(QueryConcurrencyLimited):
            async with limiter.acquire("source-e"):
                pass


async def test_slots_are_released_after_success_error_and_timeout() -> None:
    limiter = QueryLimiter(global_limit=1, per_source_limit=1, acquire_timeout=0)

    async with limiter.acquire("source-a"):
        pass
    with pytest.raises(RuntimeError):
        async with limiter.acquire("source-a"):
            raise RuntimeError("query failed")
    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.001):
            async with limiter.acquire("source-a"):
                await asyncio.sleep(1)

    async with limiter.acquire("source-a"):
        pass


async def test_slot_is_released_after_cancellation() -> None:
    limiter = QueryLimiter(global_limit=1, per_source_limit=1, acquire_timeout=0)
    entered = asyncio.Event()

    async def blocked_query() -> None:
        async with limiter.acquire("source-a"):
            entered.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(blocked_query())
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    async with limiter.acquire("source-a"):
        pass
