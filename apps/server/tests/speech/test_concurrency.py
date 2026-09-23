import asyncio
import base64
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from alembic import command
from alembic.config import Config

from datapulse.contracts.speech import (
    DigitalHumanProviderCreate,
    DigitalHumanSettingsUpdate,
    SpeechPlanRequest,
)
from datapulse.datasource.secrets import SecretBox
from datapulse.metadata import create_metadata_engine, create_session_factory
from datapulse.settings import Settings
from datapulse.speech.repository import SpeechRepository
from datapulse.speech.service import SpeechQuotaExceeded, SpeechService

pytestmark = pytest.mark.anyio


@pytest.fixture
async def repositories(tmp_path, monkeypatch):
    monkeypatch.delenv("DATAPULSE_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATAPULSE_DATA_DIR", raising=False)
    database = tmp_path / "speech.db"
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "head")
    engines = [
        create_metadata_engine(Settings(database_url=f"sqlite+aiosqlite:///{database}"))
        for _ in range(2)
    ]
    repos = [SpeechRepository(create_session_factory(engine)) for engine in engines]
    await repos[0].update_settings(DigitalHumanSettingsUpdate(cooldown_seconds=0))
    yield repos
    for engine in engines:
        await engine.dispose()


async def plan(repository, component="speaker"):
    return await repository.create_plan(
        SpeechPlanRequest(
            screen_id="screen",
            component_id=component,
            text="hello",
            provider_id="provider",
        ),
        content_hash="a" * 64,
    )


@pytest.mark.parametrize("constraint", ["daily", "cooldown"])
async def test_concurrent_services_atomically_enforce_enqueue_limits(
    repositories, constraint, monkeypatch
):
    first, second = repositories
    await first.update_settings(
        DigitalHumanSettingsUpdate(
            daily_task_limit=1 if constraint == "daily" else 100,
            cooldown_seconds=0 if constraint == "daily" else 60,
        )
    )
    item = await plan(first)
    barrier = asyncio.Barrier(2)
    for repository in repositories:
        create = repository.create_task

        async def synchronized_create(*args, _create=create, **kwargs):
            await barrier.wait()
            return await _create(*args, **kwargs)

        monkeypatch.setattr(repository, "create_task", synchronized_create)
    services = [SpeechService(repository, None) for repository in repositories]
    try:
        results = await asyncio.gather(
            *(service.queue_task(item) for service in services), return_exceptions=True
        )
        assert sum(isinstance(item, SpeechQuotaExceeded) for item in results) == 1
        assert len(await second.list_tasks()) == 1
    finally:
        for service in services:
            await service.aclose()


async def test_losing_expired_claim_cannot_fail_another_running_worker(repositories):
    first, second = repositories
    now = datetime.now(UTC)
    task = await first.create_task(await plan(first), expires_at=now + timedelta(seconds=1))
    assert (await first.mark_task_running(task.id, now)).status == "running"
    assert await second.mark_task_running(task.id, now + timedelta(seconds=2)) is None
    assert (await first.get_task(task.id)).status == "running"


async def test_late_completion_cannot_resurrect_cancelled_task(repositories):
    first, second = repositories
    now = datetime.now(UTC)
    task = await first.create_task(await plan(first))
    await first.mark_task_running(task.id, now)
    await second.cancel_task(task.id, now)
    result = await first.finish_task(task.id, status="succeeded", finished_at=now, asset_id="late")
    assert result.status == "cancelled"
    assert result.asset_id == ""


async def test_recovery_preserves_live_leases_and_only_fails_stale_work(repositories):
    first, second = repositories
    now = datetime.now(UTC)
    running = await first.create_task(await plan(first, "running"))
    queued = await first.create_task(await plan(first, "queued"))
    await first.mark_task_running(running.id, now, lease_owner="worker-a", lease_seconds=30)
    assert await second.recoverable_task_ids(now=now + timedelta(seconds=5)) == ()
    assert await first.renew_task_lease(
        running.id, "worker-a", now + timedelta(seconds=20), lease_seconds=30
    )
    assert await second.recoverable_task_ids(now=now + timedelta(seconds=35)) == ()
    assert await second.recoverable_task_ids(now=now + timedelta(seconds=51)) == (running.id,)
    assert (await first.get_task(queued.id)).status == "queued"
    assert (await first.get_task(running.id)).error_code == "SPEECH_TASK_INTERRUPTED"
    assert not await first.renew_task_lease(running.id, "worker-a", now + timedelta(seconds=52))


async def test_audio_reservations_are_atomic_and_terminal_completion_reconciles(repositories):
    from datapulse.speech.repository import SpeechQuotaRejected

    first, second = repositories
    await first.update_settings(
        DigitalHumanSettingsUpdate(
            max_speech_seconds=10,
            daily_audio_seconds_limit=10,
        )
    )
    now = datetime.now(UTC)
    tasks = [await first.create_task(await plan(first, f"speaker-{index}")) for index in range(2)]
    for index, task in enumerate(tasks):
        await repositories[index].mark_task_running(task.id, now, lease_owner=f"worker-{index}")
    reservations = await asyncio.gather(
        *(
            repository.reserve_audio(task.id, f"worker-{index}", now)
            for index, (repository, task) in enumerate(zip(repositories, tasks, strict=True))
        ),
        return_exceptions=True,
    )
    assert sum(isinstance(value, SpeechQuotaRejected) for value in reservations) == 1
    winner = next(index for index, value in enumerate(reservations) if isinstance(value, float))
    loser = 1 - winner
    completed = await repositories[winner].finish_task(
        tasks[winner].id,
        status="succeeded",
        finished_at=now,
        lease_owner=f"worker-{winner}",
        asset_id="audio",
        duration_seconds=4,
        account_usage=True,
    )
    assert completed.status == "succeeded"
    assert (await first.usage()).generated_seconds == 4
    assert await repositories[loser].reserve_audio(tasks[loser].id, f"worker-{loser}", now) == 6
    with pytest.raises(SpeechQuotaRejected):
        await repositories[loser].finish_task(
            tasks[loser].id,
            status="succeeded",
            finished_at=now,
            lease_owner=f"worker-{loser}",
            asset_id="too-long",
            duration_seconds=7,
            account_usage=True,
        )
    await repositories[loser].cancel_task(tasks[loser].id, now)
    assert (await first.usage()).generated_seconds == 4


async def test_service_heartbeat_preserves_work_through_other_process_recovery(
    repositories, monkeypatch
):
    from datapulse.speech import service as service_module

    monkeypatch.setattr(service_module, "LEASE_HEARTBEAT_SECONDS", 0.01)
    now = [datetime.now(UTC)]
    renew_after = now[0] + timedelta(seconds=40)
    requested, renewed, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    first, second = repositories
    renew = first.renew_task_lease

    async def observed_renew(*args, **kwargs):
        result = await renew(*args, **kwargs)
        if args[2] >= renew_after:
            renewed.set()
        return result

    monkeypatch.setattr(first, "renew_task_lease", observed_renew)

    async def handler(_request):
        requested.set()
        await release.wait()
        return httpx.Response(200, headers={"content-type": "audio/mpeg"}, content=b"audio")

    class Assets:
        async def upload(self, **kwargs):
            return SimpleNamespace(id="audio", media=SimpleNamespace(duration_seconds=1))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = SpeechService(
        first,
        SecretBox(base64.urlsafe_b64encode(b"k" * 32).decode()),
        clock=lambda: now[0],
        client=client,
        asset_service=Assets(),
    )
    provider = await service.create_provider(
        DigitalHumanProviderCreate(
            name="Provider",
            provider_type="openai_compatible",
            api_key="private-key",
            base_url="https://tts.example.test",
            default_voice="alloy",
        )
    )
    item = await service.create_plan(
        SpeechPlanRequest(
            screen_id="screen",
            component_id="speaker",
            text="hello",
            provider_id=provider.id,
        )
    )
    task = await service.queue_task(item)
    execution = asyncio.create_task(service.execute_task(task.id))
    try:
        await asyncio.wait_for(requested.wait(), timeout=2)
        renewed.clear()
        now[0] += timedelta(seconds=40)
        await asyncio.wait_for(renewed.wait(), timeout=2)
        assert await second.recoverable_task_ids(now=now[0] + timedelta(seconds=30)) == ()
        release.set()
        assert (await execution).status == "succeeded"
    finally:
        release.set()
        execution.cancel()
        await asyncio.gather(execution, return_exceptions=True)
        await service.aclose()
        await client.aclose()


async def test_remote_cancellation_discards_late_asset_and_releases_quota(repositories):
    first, second = repositories
    uploaded, release = asyncio.Event(), asyncio.Event()
    deleted = []

    class Assets:
        async def upload(self, **kwargs):
            uploaded.set()
            await release.wait()
            return SimpleNamespace(id="late-audio", media=SimpleNamespace(duration_seconds=1))

        async def delete(self, asset_id):
            deleted.append(asset_id)

    async def handler(_request):
        return httpx.Response(200, headers={"content-type": "audio/mpeg"}, content=b"audio")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = SpeechService(
        first,
        SecretBox(base64.urlsafe_b64encode(b"k" * 32).decode()),
        client=client,
        asset_service=Assets(),
    )
    provider = await service.create_provider(
        DigitalHumanProviderCreate(
            name="Provider",
            provider_type="openai_compatible",
            api_key="private-key",
            base_url="https://tts.example.test",
            default_voice="alloy",
        )
    )
    item = await service.create_plan(
        SpeechPlanRequest(
            screen_id="screen",
            component_id="speaker",
            text="hello",
            provider_id=provider.id,
        )
    )
    task = await service.queue_task(item)
    execution = asyncio.create_task(service.execute_task(task.id))
    try:
        await asyncio.wait_for(uploaded.wait(), timeout=2)
        await second.cancel_task(task.id, datetime.now(UTC))
        release.set()
        assert (await execution).status == "cancelled"
        assert deleted == ["late-audio"]
        assert (await second.usage()).generated_seconds == 0
    finally:
        release.set()
        execution.cancel()
        await asyncio.gather(execution, return_exceptions=True)
        await service.aclose()
        await client.aclose()
