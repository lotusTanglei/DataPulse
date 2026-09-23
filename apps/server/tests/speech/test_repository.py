import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from datapulse.contracts.speech import (
    DigitalHumanProviderCreate,
    DigitalHumanProviderUpdate,
    DigitalHumanSettingsUpdate,
    SpeechPlanRequest,
)
from datapulse.datasource.secrets import SecretEnvelope
from datapulse.metadata import create_metadata_engine, create_session_factory
from datapulse.settings import Settings
from datapulse.speech.repository import SpeechProviderNameConflict, SpeechRepository

pytestmark = pytest.mark.anyio


async def test_provider_plan_task_and_usage_are_structured(speech_repository) -> None:
    provider = await speech_repository.create_provider(
        DigitalHumanProviderCreate(name="Local TTS", provider_type="custom"),
        None,
    )
    assert provider.configured is False
    plan = await speech_repository.create_plan(
        SpeechPlanRequest(
            screen_id="screen", component_id="speaker", text="Hello", provider_id=provider.id
        ),
        content_hash="a" * 64,
    )
    task = await speech_repository.create_task(plan)
    assert task.plan_id == plan.id
    assert task.source == "runtime"
    assert task.expires_at is not None
    assert (await speech_repository.usage()).task_count == 0


async def test_expired_speech_tasks_are_not_started(speech_repository) -> None:
    provider = await speech_repository.create_provider(
        DigitalHumanProviderCreate(name="Expiry", provider_type="custom"), None
    )
    plan = await speech_repository.create_plan(
        SpeechPlanRequest(
            screen_id="screen", component_id="speaker", text="Hello", provider_id=provider.id
        ),
        content_hash="c" * 64,
    )
    task = await speech_repository.create_task(
        plan, source="threshold", priority=10, expires_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    expired = await speech_repository.mark_task_running(task.id, datetime(2026, 1, 2, tzinfo=UTC))
    assert expired.status == "failed"
    assert expired.error_code == "SPEECH_TASK_EXPIRED"
    assert expired.source == "threshold"
    assert expired.priority == 10


async def test_task_claim_is_atomic_for_concurrent_workers(speech_repository) -> None:
    provider = await speech_repository.create_provider(
        DigitalHumanProviderCreate(name="Concurrent", provider_type="custom"), None
    )
    plan = await speech_repository.create_plan(
        SpeechPlanRequest(
            screen_id="screen", component_id="speaker", text="Hello", provider_id=provider.id
        ),
        content_hash="q" * 64,
    )
    task = await speech_repository.create_task(plan)
    started = datetime(2026, 1, 2, tzinfo=UTC)
    claimed = await asyncio.gather(
        speech_repository.mark_task_running(task.id, started),
        speech_repository.mark_task_running(task.id, started),
    )

    assert sum(item is None for item in claimed) == 1
    assert sum(item is not None and item.status == "running" for item in claimed) == 1
    assert (await speech_repository.get_task(task.id)).started_at == started


async def test_queued_task_ids_use_priority_then_fifo_order(speech_repository) -> None:
    provider = await speech_repository.create_provider(
        DigitalHumanProviderCreate(name="Dispatch", provider_type="custom"), None
    )
    plans = [
        await speech_repository.create_plan(
            SpeechPlanRequest(
                screen_id="screen",
                component_id=f"speaker-{index}",
                text=f"Text {index}",
                provider_id=provider.id,
            ),
            content_hash=f"{index + 10:064x}",
        )
        for index in range(3)
    ]
    first = await speech_repository.create_task(plans[0], priority=5)
    second = await speech_repository.create_task(plans[1], priority=20)
    third = await speech_repository.create_task(plans[2], priority=5)

    assert await speech_repository.queued_task_ids() == (second.id, first.id, third.id)


async def test_playback_diagnostics_filters_and_orders_without_exposing_text(
    speech_repository,
) -> None:
    provider = await speech_repository.create_provider(
        DigitalHumanProviderCreate(name="Diagnostics", provider_type="custom"), None
    )
    first_plan = await speech_repository.create_plan(
        SpeechPlanRequest(
            screen_id="screen-a",
            component_id="speaker-a",
            text="private first text",
            provider_id=provider.id,
        ),
        content_hash="1" * 64,
    )
    second_plan = await speech_repository.create_plan(
        SpeechPlanRequest(
            screen_id="screen-b",
            component_id="speaker-b",
            text="private second text",
            provider_id=provider.id,
        ),
        content_hash="2" * 64,
    )
    first_task = await speech_repository.create_task(first_plan, source="threshold")
    second_task = await speech_repository.create_task(second_plan, source="manual")
    await speech_repository.finish_task(
        first_task.id,
        status="succeeded",
        finished_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
        asset_id="asset-first",
    )
    await speech_repository.finish_task(
        second_task.id,
        status="failed",
        finished_at=datetime(2026, 1, 2, 12, 1, tzinfo=UTC),
        error_code="SPEECH_PROVIDER_UNAVAILABLE",
    )

    diagnostics = await speech_repository.playback_diagnostics()
    assert [item.task_id for item in diagnostics] == [second_task.id, first_task.id]
    assert diagnostics[0].status == "failed"
    assert diagnostics[0].error_code == "SPEECH_PROVIDER_UNAVAILABLE"
    assert diagnostics[0].asset_id == ""
    assert not hasattr(diagnostics[0], "text")

    assert [
        item.task_id for item in await speech_repository.playback_diagnostics(screen_id="screen-a")
    ] == [first_task.id]
    assert [
        item.task_id
        for item in await speech_repository.playback_diagnostics(component_id="speaker-b")
    ] == [second_task.id]
    assert len(await speech_repository.playback_diagnostics(limit=1)) == 1


async def test_provider_names_are_unique(speech_repository) -> None:
    data = DigitalHumanProviderCreate(name="Duplicate", provider_type="custom")
    await speech_repository.create_provider(data, None)
    with pytest.raises(SpeechProviderNameConflict):
        await speech_repository.create_provider(data, None)


async def test_global_settings_are_persisted_as_a_singleton(speech_repository) -> None:
    defaults = await speech_repository.get_settings()
    assert defaults.enabled is True
    updated = await speech_repository.update_settings(
        DigitalHumanSettingsUpdate(
            daily_task_limit=3,
            default_muted=True,
            forbidden_words=("内部机密",),
            sensitive_patterns=(r"\b\d{16}\b",),
            manual_review_required=True,
        )
    )
    assert updated.daily_task_limit == 3
    assert updated.default_muted is True
    assert updated.forbidden_words == ("内部机密",)
    assert updated.sensitive_patterns == (r"\b\d{16}\b",)
    assert updated.manual_review_required is True
    assert (await speech_repository.get_settings()).daily_task_limit == 3


async def test_metrics_snapshot_aggregates_persisted_daily_worker_state(speech_repository) -> None:
    provider = await speech_repository.create_provider(
        DigitalHumanProviderCreate(name="Metrics", provider_type="custom"), None
    )
    plan = await speech_repository.create_plan(
        SpeechPlanRequest(
            screen_id="screen", component_id="speaker", text="Hello", provider_id=provider.id
        ),
        content_hash="m" * 64,
    )
    task = await speech_repository.create_task(plan)
    await speech_repository.finish_task(
        task.id, status="succeeded", finished_at=datetime.now(UTC), asset_id="asset"
    )
    await speech_repository.record_usage(
        provider_id=provider.id,
        task_count=1,
        succeeded_count=1,
        cached_count=1,
        synthesis_attempts=2,
        synthesis_failures=1,
        synthesis_total_ms=275.5,
    )

    snapshot = await speech_repository.metrics_snapshot(datetime.now(UTC))

    assert snapshot["tasks_succeeded"] == 1
    assert snapshot["cache_hits"] == 1
    assert snapshot["synthesis_attempts"] == 2
    assert snapshot["synthesis_failures"] == 1
    assert snapshot["synthesis_total_ms"] == 275.5


@pytest.mark.parametrize("existing_row", [False, True])
async def test_usage_increments_are_atomic_for_concurrent_workers(
    speech_repository, tmp_path, existing_row: bool
) -> None:
    provider = await speech_repository.create_provider(
        DigitalHumanProviderCreate(name="Atomic usage", provider_type="custom"), None
    )
    if existing_row:
        await speech_repository.record_usage(provider_id=provider.id)
    engine = create_metadata_engine(
        Settings(
            environment="test",
            data_dir=tmp_path,
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'speech.db'}",
        )
    )
    second_worker = SpeechRepository(create_session_factory(engine))
    workers = (speech_repository, second_worker)
    try:
        await asyncio.gather(
            *(
                workers[index % 2].record_usage(
                    provider_id=provider.id,
                    task_count=1,
                    failed_count=1,
                    synthesis_attempts=1,
                    synthesis_failures=1,
                    synthesis_total_ms=10,
                )
                for index in range(20)
            )
        )
    finally:
        await engine.dispose()
    usage = await speech_repository.usage()
    assert usage.task_count == 20
    assert usage.failed_count == 20
    snapshot = await speech_repository.metrics_snapshot(datetime.now(UTC))
    assert snapshot["synthesis_attempts"] == 20
    assert snapshot["synthesis_failures"] == 20
    assert snapshot["synthesis_total_ms"] == 200


async def test_synthesis_metrics_use_utc_day_and_exclude_other_periods(speech_repository) -> None:
    day = datetime(2026, 9, 10, 12, tzinfo=UTC)
    for offset, milliseconds in ((-1, 500), (0, 100), (1, 900)):
        await speech_repository.record_usage(
            provider_id="provider-a",
            now=day + timedelta(days=offset),
            synthesis_attempts=1,
            synthesis_total_ms=milliseconds,
        )
    await speech_repository.record_usage(
        provider_id="provider-b",
        now=day,
        synthesis_attempts=1,
        synthesis_failures=1,
        synthesis_total_ms=50,
    )
    snapshot = await speech_repository.metrics_snapshot(day)
    assert snapshot["synthesis_attempts"] == 2
    assert snapshot["synthesis_failures"] == 1
    assert snapshot["synthesis_total_ms"] == 150
    assert all(
        value == 0
        for value in (await speech_repository.metrics_snapshot(day + timedelta(days=2))).values()
    )


async def test_recoverable_tasks_mark_interrupted_work_without_replay(speech_repository) -> None:
    provider = await speech_repository.create_provider(
        DigitalHumanProviderCreate(name="Recovery", provider_type="custom"), None
    )
    plan = await speech_repository.create_plan(
        SpeechPlanRequest(
            screen_id="screen", component_id="speaker", text="Hello", provider_id=provider.id
        ),
        content_hash="b" * 64,
    )
    task = await speech_repository.create_task(plan)
    await speech_repository.mark_task_running(task.id, task.created_at)

    assert await speech_repository.recoverable_task_ids(
        now=task.created_at + timedelta(seconds=61)
    ) == (task.id,)
    recovered = await speech_repository.get_task(task.id)
    assert recovered.status == "failed"
    assert recovered.error_code == "SPEECH_TASK_INTERRUPTED"


async def test_provider_health_history_opens_and_closes_circuit(speech_repository) -> None:
    provider = await speech_repository.create_provider(
        DigitalHumanProviderCreate(name="Health", provider_type="custom", api_key="secret"),
        SecretEnvelope(nonce="nonce", ciphertext="ciphertext"),
    )
    checked_at = datetime(2026, 9, 9, 12, tzinfo=UTC)
    for index in range(3):
        state = await speech_repository.record_provider_health(
            provider.id,
            checked_at=checked_at + timedelta(seconds=index),
            ok=False,
            latency_ms=100 + index,
            error_code="SPEECH_PROVIDER_UNAVAILABLE",
        )
    assert state.health_status == "open"
    assert state.consecutive_failures == 3
    history = await speech_repository.provider_health(provider.id)
    assert len(history) == 3
    assert history[0].ok is False
    audit = await speech_repository.list_audit()
    assert sum(item.action == "provider.health_failed" for item in audit) == 3

    recovered = await speech_repository.record_provider_health(
        provider.id,
        checked_at=checked_at + timedelta(minutes=2),
        ok=True,
        latency_ms=12,
        error_code=None,
    )
    assert recovered.health_status == "healthy"
    assert recovered.consecutive_failures == 0


async def test_cost_report_aggregates_persisted_usage(speech_repository) -> None:
    provider = await speech_repository.create_provider(
        DigitalHumanProviderCreate(name="Priced", provider_type="custom", cost_per_minute=60),
        None,
    )
    await speech_repository.record_usage(
        provider_id=provider.id,
        task_count=2,
        succeeded_count=1,
        failed_count=1,
        generated_seconds=30,
        estimated_cost=30,
    )
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    report = await speech_repository.cost_report(
        period_start=start, period_end=start + timedelta(days=1)
    )
    assert report.total_task_count == 2
    assert report.total_generated_seconds == 30
    assert report.total_estimated_cost == 30
    assert report.rows[0].provider_name == "Priced"


async def test_provider_version_changes_speech_cache_identity(speech_repository) -> None:
    provider = await speech_repository.create_provider(
        DigitalHumanProviderCreate(name="Versioned", provider_type="custom"), None
    )
    request = SpeechPlanRequest(
        screen_id="screen", component_id="speaker", text="Hello", provider_id=provider.id
    )
    first = await speech_repository.create_plan(request, content_hash="a" * 64)
    await speech_repository.update_provider(
        provider.id,
        DigitalHumanProviderUpdate(provider_version="v2"),
        None,
        clear_secret=False,
    )
    second = await speech_repository.create_plan(
        request, content_hash="b" * 64, provider_version="v2"
    )
    assert first.provider_version == "v1"
    assert second.provider_version == "v2"


async def test_speech_plan_persists_voice_settings(speech_repository) -> None:
    provider = await speech_repository.create_provider(
        DigitalHumanProviderCreate(name="Voice settings", provider_type="custom"), None
    )
    request = SpeechPlanRequest(
        screen_id="screen",
        component_id="speaker",
        text="Hello",
        provider_id=provider.id,
        rate=1.25,
        pitch=0.8,
        volume=0.6,
    )
    plan = await speech_repository.create_plan(request, content_hash="c" * 64)
    restored = await speech_repository.get_plan(plan.id)
    assert (restored.rate, restored.pitch, restored.volume) == (1.25, 0.8, 0.6)


async def test_retention_prunes_speech_health_usage_and_audit(speech_repository) -> None:
    provider = await speech_repository.create_provider(
        DigitalHumanProviderCreate(name="Retention", provider_type="custom"), None
    )
    old = datetime.now(UTC) - timedelta(days=45)
    await speech_repository.record_provider_health(
        provider.id,
        checked_at=old,
        ok=False,
        latency_ms=1,
        error_code="OLD",
    )
    deleted = await speech_repository.prune_speech_data(datetime.now(UTC) - timedelta(days=30))
    assert deleted >= 1
    assert await speech_repository.provider_health(provider.id) == ()


async def test_detach_cached_tasks_preserves_history_and_returns_asset_ids(
    speech_repository,
) -> None:
    provider = await speech_repository.create_provider(
        DigitalHumanProviderCreate(name="Cache", provider_type="custom"), None
    )
    plan = await speech_repository.create_plan(
        SpeechPlanRequest(
            screen_id="screen", component_id="speaker", text="Cached", provider_id=provider.id
        ),
        content_hash="c" * 64,
    )
    task = await speech_repository.create_task(plan)
    await speech_repository.finish_task(
        task.id,
        status="succeeded",
        finished_at=datetime.now(UTC),
        asset_id="asset-cache",
    )
    assert await speech_repository.detach_cached_tasks(provider.id) == ("asset-cache",)
    detached = await speech_repository.get_task(task.id)
    assert detached.status == "succeeded"
    assert detached.asset_id == ""
    assert any(
        item.action == "speech.cache_cleared" for item in await speech_repository.list_audit()
    )


async def test_detach_cached_tasks_before_preserves_newer_shared_cache(speech_repository) -> None:
    provider = await speech_repository.create_provider(
        DigitalHumanProviderCreate(name="Retention cache", provider_type="custom"), None
    )
    plan = await speech_repository.create_plan(
        SpeechPlanRequest(
            screen_id="screen", component_id="speaker", text="Cached", provider_id=provider.id
        ),
        content_hash="d" * 64,
    )
    old_task = await speech_repository.create_task(plan)
    new_task = await speech_repository.create_task(plan)
    old_finished = datetime.now(UTC) - timedelta(days=45)
    await speech_repository.finish_task(
        old_task.id, status="succeeded", finished_at=old_finished, asset_id="shared-asset"
    )
    await speech_repository.finish_task(
        new_task.id, status="succeeded", finished_at=datetime.now(UTC), asset_id="shared-asset"
    )

    cutoff = datetime.now(UTC) - timedelta(days=30)
    assert await speech_repository.detach_cached_tasks_before(cutoff) == ("shared-asset",)
    assert await speech_repository.cached_asset_references("shared-asset") == 1
    assert any(
        item.action == "speech.cache_retention_cleared"
        for item in await speech_repository.list_audit()
    )
