"""Standalone durable speech worker entrypoint.

Run this process alongside the API with the same DataPulse data and secret
settings. The worker uses the persisted task table; ``mark_task_running`` is an
atomic transition, so multiple worker processes cannot execute one task twice.
"""

import asyncio

from datapulse.app import create_app
from datapulse.settings import Settings


def worker_settings() -> Settings:
    """Build settings for a worker that must not recover queued API work."""
    return Settings(
        speech_worker_enabled=True,
        speech_recover_on_startup=False,
        speech_worker_mode=True,
    )


async def run_worker(settings: Settings | None = None) -> None:
    app = create_app(settings or worker_settings())
    async with app.router.lifespan_context(app):
        await asyncio.Event().wait()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
