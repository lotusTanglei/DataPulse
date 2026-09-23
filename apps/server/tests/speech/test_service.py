import asyncio
import base64
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest

from datapulse.contracts.screen_asset import AssetMediaMetadata
from datapulse.contracts.speech import (
    DigitalHumanProviderCreate,
    DigitalHumanProviderUpdate,
    DigitalHumanSettingsUpdate,
    SpeechDraftRequest,
    SpeechPlanRequest,
)
from datapulse.datasource.secrets import SecretBox
from datapulse.speech.service import SpeechProviderUnavailable, SpeechQuotaExceeded, SpeechService

pytestmark = pytest.mark.anyio


async def test_provider_connection_test_decrypts_secret_and_checks_openai_endpoint(
    speech_repository,
) -> None:
    key = base64.urlsafe_b64encode(b"k" * 32).decode().rstrip("=")
    secret_box = SecretBox(key)

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/models"
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(200, json={"data": [{"id": "tts-1"}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = SpeechService(speech_repository, secret_box, client=client)
    try:
        provider = await service.create_provider(
            DigitalHumanProviderCreate(
                name="OpenAI compatible",
                provider_type="openai_compatible",
                base_url="https://tts.example.com/",
                api_key="test-key",
                default_voice="alloy",
            )
        )
        assert provider.configured is True
        result = await service.test_provider(provider.id)
        assert result.ok is True
        assert result.voices == ("alloy",)
    finally:
        await service.aclose()


async def test_provider_connection_failure_is_stable(speech_repository) -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    key = base64.urlsafe_b64encode(b"k" * 32).decode().rstrip("=")
    service = SpeechService(
        speech_repository,
        SecretBox(key),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    try:
        provider = await service.create_provider(
            DigitalHumanProviderCreate(
                name="Unavailable", provider_type="openai_compatible", api_key="test-key"
            )
        )
        for _ in range(3):
            result = await service.test_provider(provider.id)
            assert result.ok is False
            assert result.error_code == "SPEECH_PROVIDER_UNAVAILABLE"
        current = (await service.list_providers())[0]
        assert current.health_status == "open"
        assert current.consecutive_failures == 3
        assert len(await service.provider_health(provider.id)) == 3
    finally:
        await service.aclose()


async def test_ai_draft_is_preview_only_and_requires_allowed_context(speech_repository) -> None:
    class FakeGateway:
        async def complete_json(self, *, response_model, **_kwargs):
            return response_model(text="当前值 {{value}}", warnings=("请人工确认",))

    service = SpeechService(speech_repository, None, ai_gateway=FakeGateway())
    try:
        result = await service.draft(
            SpeechDraftRequest(
                operation="rewrite", source_text="当前值", allowed_variables=("value",)
            )
        )
        assert result.preview_only is True
        assert result.warnings == ("请人工确认",)
        with pytest.raises(SpeechProviderUnavailable) as error:
            await service.draft(SpeechDraftRequest(operation="generate"))
        assert error.value.args[0] == "SPEECH_DRAFT_CONTEXT_REQUIRED"

        class UnsafeGateway:
            async def complete_json(self, *, response_model, **_kwargs):
                return response_model(text="泄露 {{password}}", warnings=())

        unsafe = SpeechService(speech_repository, None, ai_gateway=UnsafeGateway())
        try:
            with pytest.raises(SpeechProviderUnavailable) as denied:
                await unsafe.draft(
                    SpeechDraftRequest(
                        operation="rewrite", source_text="当前值", allowed_variables=("value",)
                    )
                )
            assert denied.value.args[0] == "SPEECH_DRAFT_VARIABLE_DENIED"
        finally:
            await unsafe.aclose()
    finally:
        await service.aclose()

    audit = await speech_repository.list_audit()
    assert any(item.action == "speech.ai_draft_succeeded" for item in audit)
    assert any(item.action == "speech.ai_draft_failed" for item in audit)


async def test_execute_task_synthesizes_and_persists_asset(speech_repository) -> None:
    key = base64.urlsafe_b64encode(b"k" * 32).decode().rstrip("=")
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, headers={"content-type": "audio/mpeg"}, content=b"mp3-bytes")

    class FakeAssets:
        def __init__(self) -> None:
            self.saved = None

        async def upload(self, **kwargs):
            self.saved = kwargs
            return SimpleNamespace(
                id="asset-1", media=AssetMediaMetadata(validated=True, duration_seconds=1.25)
            )

        async def get(self, _asset_id: str):
            return self.saved

    assets = FakeAssets()
    service = SpeechService(
        speech_repository,
        SecretBox(key),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        asset_service=assets,
    )
    try:
        provider = await service.create_provider(
            DigitalHumanProviderCreate(
                name="Speech API",
                provider_type="openai_compatible",
                base_url="https://tts.example.com",
                api_key="test-key",
                default_voice="alloy",
                cost_per_minute=60,
            )
        )
        plan = await service.create_plan(
            SpeechPlanRequest(
                screen_id="screen",
                component_id="speaker",
                text="当前值为 {{value}}",
                provider_id=provider.id,
                data_fingerprint="row-1",
            )
        )
        task = await speech_repository.create_task(plan)
        result = await service.execute_task(task.id)
        assert result.status == "succeeded"
        assert result.asset_id == "asset-1"
        assert assets.saved["content"] == b"mp3-bytes"
        assert requests[0].url.path == "/audio/speech"
        assert requests[0].headers["Authorization"] == "Bearer test-key"
        usage = await service.usage()
        assert usage.generated_seconds == 1.25
        assert usage.estimated_cost == 1.25
        metrics = service.metrics()
        assert metrics.synthesis_attempts == 1
        assert metrics.synthesis_failures == 0
        assert metrics.tasks_succeeded == 1
        assert metrics.average_synthesis_ms >= 0
        persisted_metrics = await service.metrics_snapshot()
        assert persisted_metrics.synthesis_attempts == 1
        assert persisted_metrics.synthesis_failures == 0
        assert persisted_metrics.synthesis_total_ms == metrics.synthesis_total_ms
        assert persisted_metrics.average_synthesis_ms == metrics.synthesis_total_ms

        reader = SpeechService(speech_repository, None)
        try:
            assert reader.metrics().synthesis_attempts == 0
            restored = await reader.metrics_snapshot()
            assert restored.synthesis_total_ms == metrics.synthesis_total_ms
            assert restored.average_synthesis_ms == metrics.synthesis_total_ms
            cached_task = await speech_repository.create_task(plan)
            assert (await service.execute_task(cached_task.id)).status == "succeeded"
            cached_metrics = await reader.metrics_snapshot()
            assert cached_metrics.cache_hits == 1
            assert cached_metrics.synthesis_attempts == 1
            assert cached_metrics.synthesis_total_ms == metrics.synthesis_total_ms
        finally:
            await reader.aclose()
    finally:
        await service.aclose()


@pytest.mark.parametrize("provider_type", ["azure", "custom"])
async def test_service_synthesizes_with_non_openai_provider_adapters(
    speech_repository, provider_type: str
) -> None:
    key = base64.urlsafe_b64encode(b"k" * 32).decode().rstrip("=")

    async def handler(request: httpx.Request) -> httpx.Response:
        if provider_type == "azure":
            assert request.url.path == "/cognitiveservices/v1"
            assert request.headers["Ocp-Apim-Subscription-Key"] == "provider-key"
            assert request.headers["Content-Type"] == "application/ssml+xml"
        else:
            assert request.url.path == "/tts"
            assert request.headers["X-API-Key"] == "provider-key"
        return httpx.Response(200, headers={"content-type": "audio/mpeg"}, content=b"audio")

    service = SpeechService(
        speech_repository,
        SecretBox(key),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    try:
        provider = await service.create_provider(
            DigitalHumanProviderCreate(
                name=provider_type,
                provider_type=provider_type,
                base_url=(
                    "https://eastus.tts.speech.microsoft.com"
                    if provider_type == "azure"
                    else "https://tts.example.com/tts"
                ),
                api_key="provider-key",
                default_voice=("zh-CN-XiaoxiaoNeural" if provider_type == "azure" else "demo"),
            )
        )
        plan = await service.create_plan(
            SpeechPlanRequest(
                screen_id="screen",
                component_id="speaker",
                text="Hello",
                provider_id=provider.id,
                language="en-US",
            )
        )
        record = await speech_repository.provider_record(provider.id)
        audio, mime = await service._synthesize_checked(record, plan)
        assert (audio, mime) == (b"audio", "audio/mpeg")
    finally:
        await service.aclose()


async def test_voice_list_and_task_cancellation_are_persisted(speech_repository) -> None:
    key = base64.urlsafe_b64encode(b"k" * 32).decode().rstrip("=")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/voices"
        return httpx.Response(200, json={"data": [{"id": "alloy"}, {"id": "中文女声"}, "alloy"]})

    service = SpeechService(
        speech_repository,
        SecretBox(key),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    try:
        provider = await service.create_provider(
            DigitalHumanProviderCreate(
                name="Voices API",
                provider_type="openai_compatible",
                base_url="https://tts.example.com",
                api_key="test-key",
            )
        )
        assert await service.list_voices(provider.id) == ("alloy", "中文女声")
        plan = await service.create_plan(
            SpeechPlanRequest(
                screen_id="screen", component_id="speaker", text="Hello", provider_id=provider.id
            )
        )
        task = await speech_repository.create_task(plan)
        cancelled = await service.cancel_task(task.id)
        assert cancelled.status == "cancelled"
        assert (await service.cancel_task(task.id)).status == "cancelled"
        assert (await service.usage()).task_count == 1
    finally:
        await service.aclose()


async def test_task_cancellation_handles_background_task_from_another_event_loop(
    speech_repository,
) -> None:
    service = SpeechService(speech_repository, None)
    foreign_loop = asyncio.new_event_loop()
    speech_task = None
    background_task = None
    try:
        provider = await service.create_provider(
            DigitalHumanProviderCreate(name="Cross loop", provider_type="custom")
        )
        plan = await service.create_plan(
            SpeechPlanRequest(
                screen_id="screen", component_id="speaker", text="Hello", provider_id=provider.id
            )
        )
        speech_task = await speech_repository.create_task(plan)
        background_task = foreign_loop.create_task(asyncio.sleep(60))
        await asyncio.to_thread(foreign_loop.run_until_complete, asyncio.sleep(0))
        service._background_tasks[speech_task.id] = background_task
        cancelled = await service.cancel_task(speech_task.id)
        assert cancelled.status == "cancelled"
    finally:
        if speech_task is not None:
            service._background_tasks.pop(speech_task.id, None)
        if background_task is not None:
            background_task.cancel()
            def drain_foreign_task() -> None:
                asyncio.set_event_loop(foreign_loop)
                foreign_loop.run_until_complete(
                    asyncio.gather(background_task, return_exceptions=True)
                )

            await asyncio.to_thread(drain_foreign_task)
        foreign_loop.close()
        await service.aclose()


async def test_queue_obeys_persisted_global_switch_and_daily_limit(speech_repository) -> None:
    service = SpeechService(speech_repository, None)
    try:
        provider = await service.create_provider(
            DigitalHumanProviderCreate(name="Quota", provider_type="custom")
        )
        plan = await service.create_plan(
            SpeechPlanRequest(
                screen_id="screen", component_id="speaker", text="Hello", provider_id=provider.id
            )
        )
        await service.update_settings(DigitalHumanSettingsUpdate(enabled=False))
        with pytest.raises(SpeechProviderUnavailable) as disabled:
            await service.queue_task(plan)
        assert disabled.value.args[0] == "DIGITAL_HUMAN_DISABLED"

        await service.update_settings(DigitalHumanSettingsUpdate(enabled=True, daily_task_limit=1))
        first = await service.queue_task(plan)
        assert first.status == "queued"
        with pytest.raises(SpeechQuotaExceeded) as limited:
            await service.queue_task(plan)
        assert limited.value.args[0] == "SPEECH_DAILY_TASK_LIMIT"
    finally:
        await service.aclose()


async def test_content_governance_blocks_plans_drafts_and_unapproved_tasks(
    speech_repository,
) -> None:
    class FakeGateway:
        async def complete_json(self, *, response_model, **_kwargs):
            return response_model(text="包含内部机密 1234567890123456", warnings=())

    service = SpeechService(speech_repository, None, ai_gateway=FakeGateway())
    try:
        await service.update_settings(
            DigitalHumanSettingsUpdate(
                forbidden_words=("内部机密",),
                sensitive_patterns=(r"\b\d{16}\b",),
                manual_review_required=True,
            )
        )
        with pytest.raises(SpeechProviderUnavailable) as plan_error:
            await service.create_plan(
                SpeechPlanRequest(screen_id="screen", component_id="speaker", text="内部机密")
            )
        assert plan_error.value.args[0] == "SPEECH_CONTENT_FORBIDDEN_WORD"
        with pytest.raises(SpeechProviderUnavailable) as draft_error:
            await service.draft(
                SpeechDraftRequest(
                    operation="rewrite", source_text="当前值", allowed_variables=("value",)
                )
            )
        assert draft_error.value.args[0] == "SPEECH_CONTENT_FORBIDDEN_WORD"

        await service.update_settings(
            DigitalHumanSettingsUpdate(forbidden_words=(), sensitive_patterns=())
        )
        plan = await service.create_plan(
            SpeechPlanRequest(screen_id="screen", component_id="speaker", text="当前值")
        )
        await service.update_settings(DigitalHumanSettingsUpdate(manual_review_required=True))
        with pytest.raises(SpeechProviderUnavailable) as review_error:
            await service.queue_task(plan)
        assert review_error.value.args[0] == "SPEECH_MANUAL_REVIEW_REQUIRED"
        approved = await service.queue_task(plan, approved=True)
        assert approved.status == "queued"
    finally:
        await service.aclose()


async def test_execute_rechecks_governance_after_plan_was_queued(speech_repository) -> None:
    class FakeAssets:
        async def get(self, _asset_id: str):
            raise AssertionError("governed task must fail before asset lookup")

    service = SpeechService(speech_repository, None, asset_service=FakeAssets())
    try:
        plan = await service.create_plan(
            SpeechPlanRequest(screen_id="screen", component_id="speaker", text="普通播报")
        )
        task = await service.queue_task(plan)
        await service.update_settings(DigitalHumanSettingsUpdate(forbidden_words=("普通",)))
        result = await service.execute_task(task.id)
        assert result.status == "failed"
        assert result.error_code == "SPEECH_CONTENT_FORBIDDEN_WORD"
        metrics = await service.metrics_snapshot()
        assert metrics.synthesis_attempts == 0
        assert metrics.synthesis_failures == 0
        assert metrics.synthesis_total_ms == 0
    finally:
        await service.aclose()


async def test_tts_retries_with_language_fallback_when_provider_rejects_locale(
    speech_repository,
) -> None:
    key = base64.urlsafe_b64encode(b"l" * 32).decode().rstrip("=")
    languages: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        languages.append(payload["language"])
        if payload["language"] in {"zh-TW", "zh"}:
            return httpx.Response(422, json={"error": "language unsupported"})
        return httpx.Response(200, headers={"content-type": "audio/mpeg"}, content=b"mp3")

    class FakeAssets:
        async def upload(self, **kwargs):
            return SimpleNamespace(
                id="asset-fallback", media=AssetMediaMetadata(validated=True, duration_seconds=1)
            )

    service = SpeechService(
        speech_repository,
        SecretBox(key),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        asset_service=FakeAssets(),
    )
    try:
        provider = await service.create_provider(
            DigitalHumanProviderCreate(
                name="Fallback",
                provider_type="openai_compatible",
                base_url="https://tts.example.com",
                api_key="test-key",
                default_voice="alloy",
                language="zh-CN",
            )
        )
        plan = await service.create_plan(
            SpeechPlanRequest(
                screen_id="screen",
                component_id="speaker",
                text="你好",
                language="zh-TW",
                provider_id=provider.id,
            )
        )
        task = await speech_repository.create_task(plan)
        result = await service.execute_task(task.id)
        assert result.status == "succeeded"
        assert languages == ["zh-TW", "zh", "zh-CN"]
    finally:
        await service.aclose()


async def test_tts_provider_failure_does_not_try_language_fallback(
    speech_repository,
) -> None:
    key = base64.urlsafe_b64encode(b"u" * 32).decode().rstrip("=")
    languages: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        languages.append(json.loads(request.content)["language"])
        return httpx.Response(503)

    service = SpeechService(
        speech_repository,
        SecretBox(key),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        asset_service=SimpleNamespace(),
    )
    try:
        provider = await service.create_provider(
            DigitalHumanProviderCreate(
                name="No language fallback on outage",
                provider_type="openai_compatible",
                base_url="https://tts.example.com",
                api_key="test-key",
                default_voice="alloy",
                language="zh-CN",
            )
        )
        plan = await service.create_plan(
            SpeechPlanRequest(
                screen_id="screen",
                component_id="speaker",
                text="你好",
                language="zh-TW",
                provider_id=provider.id,
            )
        )
        task = await speech_repository.create_task(plan)
        result = await service.execute_task(task.id)
        assert result.status == "failed"
        assert result.error_code == "SPEECH_PROVIDER_UNAVAILABLE"
        assert languages == ["zh-TW", "zh-TW", "zh-TW"]
        metrics = await service.metrics_snapshot()
        assert metrics.synthesis_attempts == 1
        assert metrics.synthesis_failures == 1
        assert metrics.synthesis_total_ms == service.metrics().synthesis_total_ms
    finally:
        await service.aclose()


async def test_tts_mixed_language_fallback_failure_reports_final_provider_error(
    speech_repository,
) -> None:
    key = base64.urlsafe_b64encode(b"v" * 32).decode().rstrip("=")
    languages: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        language = json.loads(request.content)["language"]
        languages.append(language)
        if language == "zh-TW":
            return httpx.Response(422, json={"error": "language unsupported"})
        return httpx.Response(503)

    service = SpeechService(
        speech_repository,
        SecretBox(key),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        asset_service=SimpleNamespace(),
    )
    try:
        provider = await service.create_provider(
            DigitalHumanProviderCreate(
                name="Mixed language fallback failure",
                provider_type="openai_compatible",
                base_url="https://tts.example.com",
                api_key="test-key",
                default_voice="alloy",
                language="zh-CN",
            )
        )
        plan = await service.create_plan(
            SpeechPlanRequest(
                screen_id="screen",
                component_id="speaker",
                text="你好",
                language="zh-TW",
                provider_id=provider.id,
            )
        )
        task = await speech_repository.create_task(plan)
        result = await service.execute_task(task.id)
        assert result.status == "failed"
        assert result.error_code == "SPEECH_PROVIDER_UNAVAILABLE"
        assert languages == ["zh-TW", "zh", "zh", "zh"]
    finally:
        await service.aclose()


async def test_tts_generic_unprocessable_response_does_not_try_language_fallback(
    speech_repository,
) -> None:
    key = base64.urlsafe_b64encode(b"w" * 32).decode().rstrip("=")
    languages: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        languages.append(json.loads(request.content)["language"])
        return httpx.Response(422, json={"error": "voice is invalid"})

    service = SpeechService(
        speech_repository,
        SecretBox(key),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        asset_service=SimpleNamespace(),
    )
    try:
        provider = await service.create_provider(
            DigitalHumanProviderCreate(
                name="Generic 422",
                provider_type="openai_compatible",
                base_url="https://tts.example.com",
                api_key="test-key",
                default_voice="alloy",
                language="zh-CN",
            )
        )
        plan = await service.create_plan(
            SpeechPlanRequest(
                screen_id="screen",
                component_id="speaker",
                text="你好",
                language="zh-TW",
                provider_id=provider.id,
            )
        )
        task = await speech_repository.create_task(plan)
        result = await service.execute_task(task.id)
        assert result.status == "failed"
        assert result.error_code == "SPEECH_PROVIDER_REQUEST_REJECTED"
        assert languages == ["zh-TW"]
    finally:
        await service.aclose()


async def test_tts_plain_text_language_rejection_uses_fallback(
    speech_repository,
) -> None:
    key = base64.urlsafe_b64encode(b"x" * 32).decode().rstrip("=")
    languages: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        language = json.loads(request.content)["language"]
        languages.append(language)
        if language in {"en-GB", "en"}:
            return httpx.Response(422, text="locale not supported")
        return httpx.Response(200, headers={"content-type": "audio/mpeg"}, content=b"mp3")

    class FakeAssets:
        async def upload(self, **kwargs):
            return SimpleNamespace(
                id="asset-plain-text-fallback",
                media=AssetMediaMetadata(validated=True, duration_seconds=1),
            )

    service = SpeechService(
        speech_repository,
        SecretBox(key),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        asset_service=FakeAssets(),
    )
    try:
        provider = await service.create_provider(
            DigitalHumanProviderCreate(
                name="Plain text fallback",
                provider_type="openai_compatible",
                base_url="https://tts.example.com",
                api_key="test-key",
                default_voice="alloy",
                language="en-US",
            )
        )
        plan = await service.create_plan(
            SpeechPlanRequest(
                screen_id="screen",
                component_id="speaker",
                text="Hello",
                language="en-GB",
                provider_id=provider.id,
            )
        )
        task = await speech_repository.create_task(plan)
        result = await service.execute_task(task.id)
        assert result.status == "succeeded"
        assert languages == ["en-GB", "en", "en-US"]
    finally:
        await service.aclose()


async def test_provider_version_is_part_of_service_cache_hash(speech_repository) -> None:
    service = SpeechService(speech_repository, None)
    try:
        provider = await service.create_provider(
            DigitalHumanProviderCreate(name="Version", provider_type="custom")
        )
        request = SpeechPlanRequest(
            screen_id="screen", component_id="speaker", text="Hello", provider_id=provider.id
        )
        first = await service.create_plan(request)
        await service.update_provider(
            provider.id,
            DigitalHumanProviderUpdate(provider_version="v2"),
        )
        second = await service.create_plan(request)
        assert first.provider_version == "v1"
        assert second.provider_version == "v2"
        assert first.content_hash != second.content_hash
    finally:
        await service.aclose()


async def test_queue_applies_component_cooldown(speech_repository) -> None:
    service = SpeechService(speech_repository, None)
    try:
        provider = await service.create_provider(
            DigitalHumanProviderCreate(name="Cooldown", provider_type="custom")
        )
        plan = await service.create_plan(
            SpeechPlanRequest(
                screen_id="screen", component_id="speaker", text="Hello", provider_id=provider.id
            )
        )
        await service.update_settings(
            DigitalHumanSettingsUpdate(daily_task_limit=10, cooldown_seconds=60)
        )
        await service.queue_task(plan)
        with pytest.raises(SpeechQuotaExceeded) as error:
            await service.queue_task(plan)
        assert error.value.args[0] == "SPEECH_COOLDOWN_ACTIVE"
    finally:
        await service.aclose()


async def test_clear_cache_deletes_only_unreferenced_audio_assets(speech_repository) -> None:
    class CacheAssets:
        def __init__(self) -> None:
            self.deleted: list[str] = []

        async def references(self, _asset_id: str):
            return ()

        async def delete(self, asset_id: str):
            self.deleted.append(asset_id)

    assets = CacheAssets()
    service = SpeechService(speech_repository, None, asset_service=assets)
    try:
        provider = await service.create_provider(
            DigitalHumanProviderCreate(name="Cache service", provider_type="custom")
        )
        plan = await service.create_plan(
            SpeechPlanRequest(
                screen_id="screen", component_id="speaker", text="Cached", provider_id=provider.id
            )
        )
        task = await speech_repository.create_task(plan)
        await speech_repository.finish_task(
            task.id,
            status="succeeded",
            finished_at=plan.created_at,
            asset_id="asset-cache",
        )
        result = await service.clear_cache(provider.id)
        assert result.detached_task_count == 1
        assert result.deleted_asset_count == 1
        assert assets.deleted == ["asset-cache"]
    finally:
        await service.aclose()


async def test_prune_retained_data_reclaims_expired_cache_without_deleting_shared_asset(
    speech_repository,
) -> None:
    class CacheAssets:
        def __init__(self) -> None:
            self.deleted: list[str] = []

        async def references(self, _asset_id: str):
            return ()

        async def delete(self, asset_id: str):
            self.deleted.append(asset_id)

    assets = CacheAssets()
    service = SpeechService(speech_repository, None, asset_service=assets)
    try:
        provider = await service.create_provider(
            DigitalHumanProviderCreate(name="Retention service", provider_type="custom")
        )
        plan = await service.create_plan(
            SpeechPlanRequest(
                screen_id="screen", component_id="speaker", text="Cached", provider_id=provider.id
            )
        )
        old_task = await speech_repository.create_task(plan)
        new_task = await speech_repository.create_task(plan)
        expired_task = await speech_repository.create_task(plan)
        await speech_repository.finish_task(
            old_task.id,
            status="succeeded",
            finished_at=datetime.now(UTC) - timedelta(days=45),
            asset_id="shared-asset",
        )
        await speech_repository.finish_task(
            new_task.id,
            status="succeeded",
            finished_at=datetime.now(UTC),
            asset_id="shared-asset",
        )
        await speech_repository.finish_task(
            expired_task.id,
            status="succeeded",
            finished_at=datetime.now(UTC) - timedelta(days=45),
            asset_id="expired-asset",
        )
        await service.update_settings(DigitalHumanSettingsUpdate(data_retention_days=30))

        await service.prune_retained_data()

        assert assets.deleted == ["expired-asset"]
        assert (await speech_repository.get_task(old_task.id)).asset_id == ""
        assert (await speech_repository.get_task(new_task.id)).asset_id == "shared-asset"
    finally:
        await service.aclose()
