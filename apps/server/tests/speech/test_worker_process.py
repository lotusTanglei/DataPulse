"""Real process ownership/restart regression, using an isolated SQLite fixture."""

import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta

import pytest

from datapulse.contracts.speech import SpeechPlanRequest
from datapulse.metadata import create_metadata_engine, create_session_factory
from datapulse.settings import Settings
from datapulse.speech.repository import SpeechRepository
from tests.support.app import migrate_database

pytestmark = pytest.mark.anyio


async def test_killed_worker_cannot_be_reclaimed_or_replayed(tmp_path):
    database = tmp_path / "metadata.db"
    migrate_database(database)
    url = f"sqlite+aiosqlite:///{database}"
    engine = create_metadata_engine(Settings(database_url=url))
    repository = SpeechRepository(create_session_factory(engine))
    child = None
    try:
        plan = await repository.create_plan(
            SpeechPlanRequest(screen_id="fixture", component_id="speaker", text="hello"),
            content_hash="a" * 64,
        )
        task = await repository.create_task(plan)
        program = """
import asyncio,json,sys
from datetime import UTC,datetime
from datapulse.metadata import create_metadata_engine,create_session_factory
from datapulse.settings import Settings
from datapulse.speech.repository import SpeechRepository
async def main():
    engine=create_metadata_engine(Settings(database_url=sys.argv[1]))
    repository=SpeechRepository(create_session_factory(engine))
    task=await repository.mark_task_running(
        sys.argv[2],datetime.now(UTC),lease_owner='fixture-worker')
    print(json.dumps({'status':task.status}),flush=True)
    await asyncio.Event().wait()
asyncio.run(main())
"""
        child = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            program,
            url,
            task.id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        claimed = json.loads(await asyncio.wait_for(child.stdout.readline(), timeout=15))
        assert claimed == {"status": "running"}
        now = datetime.now(UTC)
        assert await repository.mark_task_running(task.id, now) is None
        assert await repository.recoverable_task_ids(now=now) == ()
        child.kill()
        await child.wait()
        # Move the recovery clock past the durable lease; no 60-second sleep required.
        assert await repository.recoverable_task_ids(now=now + timedelta(seconds=61)) == (task.id,)
        recovered = await repository.get_task(task.id)
        assert recovered.status == "failed"
        assert recovered.error_code == "SPEECH_TASK_INTERRUPTED"
        assert await repository.mark_task_running(task.id, now + timedelta(seconds=62)) is None
    finally:
        if child is not None and child.returncode is None:
            child.kill()
            await child.wait()
        await engine.dispose()
