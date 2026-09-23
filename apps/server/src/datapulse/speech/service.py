import asyncio
import hashlib
import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

from datapulse.ai.gateway import AiGateway
from datapulse.contracts.speech import (
    DigitalHumanAuditResponse,
    DigitalHumanCacheClearResponse,
    DigitalHumanCostReportResponse,
    DigitalHumanMetricsResponse,
    DigitalHumanPlaybackDiagnosticResponse,
    DigitalHumanProviderCreate,
    DigitalHumanProviderHealthResponse,
    DigitalHumanProviderResponse,
    DigitalHumanProviderTestResponse,
    DigitalHumanProviderUpdate,
    DigitalHumanSettingsResponse,
    DigitalHumanSettingsUpdate,
    DigitalHumanUsageResponse,
    SpeechDraftRequest,
    SpeechDraftResponse,
    SpeechPlanRequest,
    SpeechPlanResponse,
    SpeechTaskResponse,
)
from datapulse.contracts.speech_template import parse_speech_template, sensitive_speech_field
from datapulse.datasource.secrets import SecretBox, SecretEnvelope
from datapulse.screen.assets import AssetInUse, AssetNotFound, AssetService
from datapulse.speech.providers import (
    ProviderProtocolError,
    ProviderRequest,
)
from datapulse.speech.providers import (
    check_provider as provider_test,
)
from datapulse.speech.providers import (
    list_voices as provider_list_voices,
)
from datapulse.speech.providers import (
    synthesize as provider_synthesize,
)
from datapulse.speech.repository import SpeechQuotaRejected, SpeechRepository


class SpeechProviderUnavailable(RuntimeError):
    code = "SPEECH_PROVIDER_UNAVAILABLE"


class SpeechQuotaExceeded(RuntimeError):
    code = "SPEECH_QUOTA_EXCEEDED"


logger = logging.getLogger(__name__)
LEASE_SECONDS = 60
LEASE_HEARTBEAT_SECONDS = 10


@dataclass
class _SpeechMetrics:
    tasks_queued: int = 0
    tasks_succeeded: int = 0
    tasks_failed: int = 0
    tasks_cancelled: int = 0
    cache_hits: int = 0
    synthesis_attempts: int = 0
    synthesis_failures: int = 0
    synthesis_total_ms: float = 0


class SpeechService:
    def __init__(
        self,
        repository: SpeechRepository,
        secret_box: SecretBox | None,
        *,
        clock: Callable[[], datetime] | None = None,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 15,
        ai_gateway: AiGateway | None = None,
        asset_service: AssetService | None = None,
    ) -> None:
        self._repository = repository
        self._secret_box = secret_box
        self._clock = clock or (lambda: datetime.now(UTC))
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None
        self._timeout_seconds = timeout_seconds
        self._ai_gateway = ai_gateway
        self._asset_service = asset_service
        self._background_tasks: dict[str, asyncio.Task[object]] = {}
        self._worker_task: asyncio.Task[object] | None = None
        self._metrics = _SpeechMetrics()

    async def aclose(self) -> None:
        if self._worker_task is not None:
            self._worker_task.cancel()
            await asyncio.gather(self._worker_task, return_exceptions=True)
            self._worker_task = None
        for task in tuple(self._background_tasks.values()):
            task.cancel()
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks.values(), return_exceptions=True)
        if self._owns_client:
            await self._client.aclose()

    async def start_worker(self, *, poll_seconds: float = 0.25) -> None:
        if self._asset_service is None or self._worker_task is not None:
            return

        async def worker() -> None:
            next_recovery = 0.0
            while True:
                try:
                    if time.monotonic() >= next_recovery:
                        await self.recover_pending_tasks()
                        next_recovery = time.monotonic() + LEASE_HEARTBEAT_SECONDS
                    for task_id in await self._repository.queued_task_ids(limit=20):
                        self._schedule(task_id)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    # A transient database failure must not permanently kill the worker.
                    pass
                await asyncio.sleep(poll_seconds)

        self._worker_task = asyncio.create_task(worker())

    def _encrypt(self, provider_id: str, value: str) -> SecretEnvelope:
        if self._secret_box is None:
            raise SpeechProviderUnavailable("SPEECH_PROVIDER_SECRET_KEY_MISSING")
        return self._secret_box.encrypt_for(provider_id, "tts-api-key", value)

    async def list_providers(self) -> tuple[DigitalHumanProviderResponse, ...]:
        return await self._repository.list_providers()

    async def get_settings(self) -> DigitalHumanSettingsResponse:
        return await self._repository.get_settings()

    async def update_settings(
        self, data: DigitalHumanSettingsUpdate
    ) -> DigitalHumanSettingsResponse:
        return await self._repository.update_settings(data)

    async def create_provider(
        self, data: DigitalHumanProviderCreate
    ) -> DigitalHumanProviderResponse:
        provider_id = str(uuid4())
        envelope = (
            self._encrypt(provider_id, data.api_key.get_secret_value()) if data.api_key else None
        )
        return await self._repository.create_provider(data, envelope, provider_id=provider_id)

    async def update_provider(
        self, provider_id: str, data: DigitalHumanProviderUpdate
    ) -> DigitalHumanProviderResponse:
        envelope = (
            self._encrypt(provider_id, data.api_key.get_secret_value()) if data.api_key else None
        )
        return await self._repository.update_provider(
            provider_id, data, envelope, clear_secret=data.clear_api_key
        )

    async def delete_provider(self, provider_id: str) -> None:
        await self._repository.delete_provider(provider_id)

    async def test_provider(self, provider_id: str) -> DigitalHumanProviderTestResponse:
        record = await self._repository.provider_record(provider_id)
        started = time.perf_counter()
        if not record.enabled:
            return await self._health_result(
                record.id,
                DigitalHumanProviderTestResponse(
                    ok=False, latency_ms=0, error_code="SPEECH_PROVIDER_DISABLED"
                ),
            )
        if record.secret_envelope is None:
            return await self._health_result(
                record.id,
                DigitalHumanProviderTestResponse(
                    ok=False, latency_ms=0, error_code="SPEECH_PROVIDER_NOT_CONFIGURED"
                ),
            )
        if self._secret_box is None:
            return await self._health_result(
                record.id,
                DigitalHumanProviderTestResponse(
                    ok=False, latency_ms=0, error_code="SPEECH_PROVIDER_SECRET_KEY_MISSING"
                ),
            )
        try:
            envelope = SecretEnvelope.model_validate_json(record.secret_envelope)
            api_key = self._secret_box.decrypt_for(record.id, "tts-api-key", envelope)
            voices = await provider_test(
                record.provider_type,
                record.base_url,
                ProviderRequest(self._client, self._timeout_seconds, api_key),
            )
        except ProviderProtocolError as error:
            return await self._health_result(
                record.id,
                DigitalHumanProviderTestResponse(
                    ok=False,
                    latency_ms=max(0, round((time.perf_counter() - started) * 1000)),
                    error_code=str(error.args[0]) if error.args else "SPEECH_PROVIDER_UNAVAILABLE",
                ),
            )
        except (httpx.HTTPError, ValueError):
            return await self._health_result(
                record.id,
                DigitalHumanProviderTestResponse(
                    ok=False,
                    latency_ms=max(0, round((time.perf_counter() - started) * 1000)),
                    error_code="SPEECH_PROVIDER_UNAVAILABLE",
                ),
            )
        latency = max(0, round((time.perf_counter() - started) * 1000))
        return await self._health_result(
            record.id,
            DigitalHumanProviderTestResponse(
                ok=True,
                latency_ms=latency,
                voices=voices or ((record.default_voice,) if record.default_voice else ()),
            ),
        )

    async def _health_result(
        self, provider_id: str, result: DigitalHumanProviderTestResponse
    ) -> DigitalHumanProviderTestResponse:
        try:
            await self._repository.record_provider_health(
                provider_id,
                checked_at=self._clock(),
                ok=result.ok,
                latency_ms=result.latency_ms,
                error_code=result.error_code,
            )
        except Exception:
            # A diagnostic write must never hide the provider test result.
            pass
        return result

    async def create_plan(self, data: SpeechPlanRequest) -> SpeechPlanResponse:
        settings = await self._repository.get_settings()
        self._validate_governed_text(data.text, settings)
        provider_version = "v1"
        if data.provider_id:
            provider = await self._repository.provider_record(data.provider_id)
            provider_version = provider.provider_version
        content_hash = hashlib.sha256(
            f"{data.text}\x00{data.language}\x00{data.provider_id}\x00{provider_version}\x00{data.voice}\x00{data.rate}\x00{data.pitch}\x00{data.volume}\x00{data.data_fingerprint}".encode()
        ).hexdigest()
        return await self._repository.create_plan(
            data, content_hash=content_hash, provider_version=provider_version
        )

    async def queue_task(
        self,
        plan: SpeechPlanResponse,
        *,
        source: str = "runtime",
        priority: int = 0,
        ttl_seconds: int = 300,
        approved: bool = False,
        request_id: str | None = None,
    ) -> SpeechTaskResponse:
        settings = await self._repository.get_settings()
        if not settings.enabled:
            raise SpeechProviderUnavailable("DIGITAL_HUMAN_DISABLED")
        self._validate_governed_text(plan.text, settings)
        if settings.manual_review_required and not approved:
            raise SpeechProviderUnavailable("SPEECH_MANUAL_REVIEW_REQUIRED")
        now = self._clock()
        try:
            task = await self._repository.create_task(
                plan,
                source=source[:64] or "runtime",
                priority=max(-100, min(100, priority)),
                expires_at=now + timedelta(seconds=max(1, min(ttl_seconds, 86_400))),
                now=now,
                enforce_limits=True,
            )
        except SpeechQuotaRejected as error:
            if str(error) == "DIGITAL_HUMAN_DISABLED":
                raise SpeechProviderUnavailable(str(error)) from error
            raise SpeechQuotaExceeded(str(error)) from error
        self._metrics.tasks_queued += 1
        logger.info(
            "digital_human_speech_task_queued",
            extra={
                "speech_task_id": task.id,
                "screen_id": plan.screen_id,
                "component_id": plan.component_id,
                "provider_id": plan.provider_id,
                "status": task.status,
                "request_id": request_id or f"speech:{task.id}",
            },
        )
        return task

    def _schedule(self, task_id: str) -> None:
        if self._asset_service is None or task_id in self._background_tasks:
            return
        background = asyncio.create_task(self.execute_task(task_id))
        self._background_tasks[task_id] = background
        background.add_done_callback(
            lambda _done, task_id=task_id: self._background_tasks.pop(task_id, None)
        )

    async def recover_pending_tasks(self) -> int:
        task_ids = await self._repository.recoverable_task_ids(now=self._clock())
        return len(task_ids)

    async def prune_retained_data(self) -> int:
        settings = await self._repository.get_settings()
        cutoff = self._clock() - timedelta(days=settings.data_retention_days)
        cache_asset_ids = await self._repository.detach_cached_tasks_before(cutoff)
        deleted_assets = 0
        if self._asset_service is not None:
            for asset_id in set(cache_asset_ids):
                if await self._repository.cached_asset_references(asset_id):
                    continue
                try:
                    if await self._asset_service.references(asset_id):
                        continue
                    await self._asset_service.delete(asset_id)
                    deleted_assets += 1
                except (AssetInUse, AssetNotFound):
                    continue
        return (await self._repository.prune_speech_data(cutoff)) + deleted_assets

    async def queue_task_by_id(
        self, plan_id: str, *, approved: bool = False, request_id: str | None = None
    ) -> SpeechTaskResponse:
        return await self.queue_task(
            await self._repository.get_plan(plan_id), approved=approved, request_id=request_id
        )

    async def get_task(self, task_id: str) -> SpeechTaskResponse:
        return await self._repository.get_task(task_id)

    async def list_tasks(
        self, *, status: str | None = None, limit: int = 50
    ) -> tuple[SpeechTaskResponse, ...]:
        return await self._repository.list_tasks(status=status, limit=limit)

    async def playback_diagnostics(
        self,
        *,
        screen_id: str | None = None,
        component_id: str | None = None,
        limit: int = 50,
    ) -> tuple[DigitalHumanPlaybackDiagnosticResponse, ...]:
        return await self._repository.playback_diagnostics(
            screen_id=screen_id,
            component_id=component_id,
            limit=limit,
        )

    async def cancel_task(self, task_id: str) -> SpeechTaskResponse:
        before = await self._repository.get_task(task_id)
        if before.status not in {"queued", "running"}:
            return before
        background = self._background_tasks.get(task_id)
        if background is not None:
            background_loop = background.get_loop()
            current_loop = asyncio.get_running_loop()
            if background_loop is current_loop:
                background.cancel()
                await asyncio.gather(background, return_exceptions=True)
            elif not background.done():
                if background_loop.is_running():
                    background_loop.call_soon_threadsafe(background.cancel)
                else:
                    background.cancel()
        task = await self._repository.cancel_task(task_id, self._clock())
        self._metrics.tasks_cancelled += 1
        logger.info(
            "digital_human_speech_task_cancelled",
            extra={
                "speech_task_id": task_id,
                "provider_id": task.provider_id,
                "status": task.status,
                "request_id": f"speech:{task_id}",
            },
        )
        await self._repository.record_usage(
            provider_id=task.provider_id, task_count=1, now=self._clock()
        )
        return task

    async def list_voices(self, provider_id: str) -> tuple[str, ...]:
        record = await self._repository.provider_record(provider_id)
        if record.circuit_open_until is not None and record.circuit_open_until > self._clock():
            raise SpeechProviderUnavailable("SPEECH_PROVIDER_CIRCUIT_OPEN")
        if not record.enabled:
            raise SpeechProviderUnavailable("SPEECH_PROVIDER_DISABLED")
        if self._secret_box is None or record.secret_envelope is None or not record.base_url:
            raise SpeechProviderUnavailable("SPEECH_PROVIDER_NOT_CONFIGURED")
        try:
            envelope = SecretEnvelope.model_validate_json(record.secret_envelope)
            api_key = self._secret_box.decrypt_for(record.id, "tts-api-key", envelope)
            voices = await provider_list_voices(
                record.provider_type,
                record.base_url,
                ProviderRequest(self._client, self._timeout_seconds, api_key),
            )
        except ProviderProtocolError as error:
            error_code = str(error.args[0]) if error.args else "SPEECH_PROVIDER_VOICES_UNAVAILABLE"
            try:
                await self._repository.record_provider_health(
                    provider_id,
                    checked_at=self._clock(),
                    ok=False,
                    latency_ms=0,
                    error_code=error_code,
                )
            except Exception:
                pass
            raise SpeechProviderUnavailable(error_code) from error
        except (httpx.HTTPError, ValueError, TypeError) as error:
            try:
                await self._repository.record_provider_health(
                    provider_id,
                    checked_at=self._clock(),
                    ok=False,
                    latency_ms=0,
                    error_code="SPEECH_PROVIDER_VOICES_UNAVAILABLE",
                )
            except Exception:
                pass
            raise SpeechProviderUnavailable("SPEECH_PROVIDER_VOICES_UNAVAILABLE") from error
        try:
            await self._repository.record_provider_health(
                provider_id,
                checked_at=self._clock(),
                ok=True,
                latency_ms=0,
                error_code=None,
            )
        except Exception:
            pass
        return voices

    async def execute_task(self, task_id: str) -> SpeechTaskResponse:
        """Run one queued task and persist both its result and billable usage."""
        if self._asset_service is None:
            raise SpeechProviderUnavailable("SPEECH_ASSET_SERVICE_NOT_CONFIGURED")
        started = self._clock()
        lease_owner = str(uuid4())
        task = await self._repository.mark_task_running(
            task_id, started, lease_owner=lease_owner, lease_seconds=LEASE_SECONDS
        )
        if task is None:
            return await self._repository.get_task(task_id)
        if task.status != "running":
            return task
        owner_task = asyncio.current_task()

        async def heartbeat() -> None:
            while True:
                await asyncio.sleep(LEASE_HEARTBEAT_SECONDS)
                try:
                    owned = await self._repository.renew_task_lease(
                        task_id, lease_owner, self._clock(), lease_seconds=LEASE_SECONDS
                    )
                except Exception:
                    owned = False
                if not owned:
                    if owner_task is not None:
                        owner_task.cancel()
                    return

        heartbeat_task = asyncio.create_task(heartbeat())
        try:
            return await self._execute_claimed_task(task, lease_owner)
        finally:
            heartbeat_task.cancel()
            await asyncio.gather(heartbeat_task, return_exceptions=True)

    async def _execute_claimed_task(
        self, task: SpeechTaskResponse, lease_owner: str
    ) -> SpeechTaskResponse:
        task_id = task.id
        created_asset_id: str | None = None
        try:
            plan = await self._repository.get_plan(task.plan_id)
            settings = await self._repository.get_settings()
            self._validate_governed_text(plan.text, settings)
            cached = await self._repository.cached_task(plan)
            if cached and cached.asset_id:
                try:
                    await self._asset_service.get(cached.asset_id)
                except Exception:
                    cached = None
            if cached and cached.asset_id:
                self._metrics.cache_hits += 1
                result = await self._repository.finish_task(
                    task_id,
                    status="succeeded",
                    finished_at=self._clock(),
                    asset_id=cached.asset_id,
                    lease_owner=lease_owner,
                    cache_hit=True,
                    account_usage=True,
                )
                if result.status != "succeeded":
                    return result
                self._metrics.tasks_succeeded += 1
                logger.info(
                    "digital_human_speech_task_finished",
                    extra={
                        "speech_task_id": task_id,
                        "provider_id": plan.provider_id,
                        "status": "succeeded",
                        "cache_hit": True,
                        "request_id": f"speech:{task_id}",
                    },
                )
                return result

            record = await self._repository.provider_record(plan.provider_id)
            await self._repository.reserve_audio(task_id, lease_owner, self._clock())
            self._metrics.synthesis_attempts += 1
            synthesis_failed = False
            synthesis_started = time.perf_counter()
            try:
                audio, mime_type = await self._synthesize(record, plan)
            except Exception:
                self._metrics.synthesis_failures += 1
                synthesis_failed = True
                raise
            finally:
                synthesis_total_ms = (time.perf_counter() - synthesis_started) * 1000
                self._metrics.synthesis_total_ms += synthesis_total_ms
                await self._repository.record_usage(
                    provider_id=plan.provider_id,
                    synthesis_attempts=1,
                    synthesis_failures=int(synthesis_failed),
                    synthesis_total_ms=synthesis_total_ms,
                    now=self._clock(),
                )
            extension = {
                "audio/mpeg": "mp3",
                "audio/mp3": "mp3",
                "audio/ogg": "ogg",
                "audio/wav": "wav",
            }.get(mime_type)
            if extension is None:
                raise SpeechProviderUnavailable("SPEECH_PROVIDER_INVALID_AUDIO")
            asset = await self._asset_service.upload(
                filename=f"speech-{task_id}.{extension}",
                content_type=mime_type,
                content=audio,
                uploaded_by="digital-human",
            )
            created_asset_id = asset.id
            duration = float(asset.media.duration_seconds or 0)
            result = await self._repository.finish_task(
                task_id,
                status="succeeded",
                finished_at=self._clock(),
                asset_id=asset.id,
                lease_owner=lease_owner,
                duration_seconds=duration,
                estimated_cost=duration / 60 * record.cost_per_minute,
                account_usage=True,
            )
            if result.status != "succeeded":
                return result
            self._metrics.tasks_succeeded += 1
            logger.info(
                "digital_human_speech_task_finished",
                extra={
                    "speech_task_id": task_id,
                    "provider_id": plan.provider_id,
                    "status": "succeeded",
                    "duration_seconds": duration,
                    "cache_hit": False,
                    "request_id": f"speech:{task_id}",
                },
            )
            return result
        except asyncio.CancelledError:
            await self._repository.finish_task(
                task_id,
                status="failed",
                finished_at=self._clock(),
                lease_owner=lease_owner,
                error_code="SPEECH_TASK_INTERRUPTED",
                account_usage=True,
            )
            raise
        except Exception as error:
            error_code = (
                error.args[0]
                if isinstance(
                    error, (SpeechProviderUnavailable, SpeechQuotaExceeded, SpeechQuotaRejected)
                )
                and error.args
                else getattr(error, "code", None) or "SPEECH_TASK_FAILED"
            )
            result = await self._repository.finish_task(
                task_id,
                status="failed",
                finished_at=self._clock(),
                error_code=error_code,
                lease_owner=lease_owner,
                account_usage=True,
            )
            if result.status != "failed":
                return result
            self._metrics.tasks_failed += 1
            logger.warning(
                "digital_human_speech_task_failed",
                extra={
                    "speech_task_id": task_id,
                    "provider_id": task.provider_id,
                    "status": "failed",
                    "error_code": error_code,
                    "request_id": f"speech:{task_id}",
                },
            )
            return result
        finally:
            if created_asset_id is not None:
                try:
                    current = await self._repository.get_task(task_id)
                    if current.asset_id != created_asset_id:
                        await self._asset_service.delete(created_asset_id)
                except Exception:
                    logger.warning(
                        "digital_human_orphan_asset_cleanup_failed",
                        extra={
                            "request_id": f"speech:{task_id}",
                            "error_code": "SPEECH_ASSET_CLEANUP_FAILED",
                        },
                    )

    async def _synthesize(self, record, plan: SpeechPlanResponse) -> tuple[bytes, str]:
        if record.circuit_open_until is not None and record.circuit_open_until > self._clock():
            raise SpeechProviderUnavailable("SPEECH_PROVIDER_CIRCUIT_OPEN")
        try:
            return await self._synthesize_checked(record, plan)
        except Exception as error:
            try:
                await self._repository.record_provider_health(
                    record.id,
                    checked_at=self._clock(),
                    ok=False,
                    latency_ms=0,
                    error_code=getattr(error, "args", [None])[0] or "SPEECH_PROVIDER_UNAVAILABLE",
                )
            except Exception:
                pass
            raise

    async def _synthesize_checked(self, record, plan: SpeechPlanResponse) -> tuple[bytes, str]:
        if not record.enabled:
            raise SpeechProviderUnavailable("SPEECH_PROVIDER_DISABLED")
        if not record.base_url:
            raise SpeechProviderUnavailable("SPEECH_PROVIDER_NOT_CONFIGURED")
        if self._secret_box is None or record.secret_envelope is None:
            raise SpeechProviderUnavailable("SPEECH_PROVIDER_NOT_CONFIGURED")
        try:
            envelope = SecretEnvelope.model_validate_json(record.secret_envelope)
            api_key = self._secret_box.decrypt_for(record.id, "tts-api-key", envelope)
        except (ValueError, TypeError) as error:
            raise SpeechProviderUnavailable("SPEECH_PROVIDER_SECRET_INVALID") from error
        voice = plan.voice or record.default_voice
        if not voice:
            raise SpeechProviderUnavailable("SPEECH_PROVIDER_VOICE_REQUIRED")
        last_error: Exception | None = None
        provider_error_code: str | None = None
        languages = self._language_candidates(plan.language, record.language)
        language_unsupported = False
        for language_index, language in enumerate(languages):
            language_fallback_requested = False
            for attempt in range(3):
                try:
                    _audio, content_type, response = await provider_synthesize(
                        record.provider_type,
                        record.base_url,
                        ProviderRequest(self._client, self._timeout_seconds, api_key),
                        text=plan.text,
                        language=language,
                        voice=voice,
                        rate=plan.rate,
                        pitch=plan.pitch,
                        volume=plan.volume,
                    )
                    if response.status_code < 400:
                        try:
                            await self._repository.record_provider_health(
                                record.id,
                                checked_at=self._clock(),
                                ok=True,
                                latency_ms=0,
                                error_code=None,
                            )
                        except Exception:
                            pass
                        return _audio, content_type
                    if (
                        response.status_code == 422
                        and self._is_language_unsupported(response)
                        and language_index < len(languages) - 1
                    ):
                        language_unsupported = True
                        language_fallback_requested = True
                        last_error = SpeechProviderUnavailable(
                            "SPEECH_PROVIDER_LANGUAGE_UNSUPPORTED"
                        )
                        break
                    if response.status_code == 422 and self._is_language_unsupported(response):
                        language_unsupported = True
                        last_error = SpeechProviderUnavailable(
                            "SPEECH_PROVIDER_LANGUAGE_UNSUPPORTED"
                        )
                        break
                    language_unsupported = False
                    if response.status_code not in {408, 429} and response.status_code < 500:
                        raise SpeechProviderUnavailable("SPEECH_PROVIDER_REQUEST_REJECTED")
                    last_error = SpeechProviderUnavailable("SPEECH_PROVIDER_UNAVAILABLE")
                except ProviderProtocolError as error:
                    language_unsupported = False
                    provider_error_code = (
                        str(error.args[0]) if error.args else "SPEECH_PROVIDER_UNAVAILABLE"
                    )
                    last_error = SpeechProviderUnavailable(provider_error_code)
                    break
                except httpx.HTTPError as error:
                    language_unsupported = False
                    last_error = error
                if attempt < 2:
                    await asyncio.sleep(0.2 * (2**attempt))
            if language_fallback_requested:
                continue
            if last_error is not None:
                break
        error_code = (
            "SPEECH_PROVIDER_LANGUAGE_UNSUPPORTED"
            if language_unsupported
            else provider_error_code or "SPEECH_PROVIDER_UNAVAILABLE"
        )
        raise SpeechProviderUnavailable(error_code) from last_error

    @staticmethod
    def _is_language_unsupported(response: httpx.Response) -> bool:
        """Only downgrade an explicit language/locale rejection, never a generic 422."""
        try:
            payload = response.json()
        except (ValueError, TypeError):
            payload = response.text

        def strings(value: object):
            if isinstance(value, str):
                yield value
            elif isinstance(value, dict):
                for nested in value.values():
                    yield from strings(nested)
            elif isinstance(value, list):
                for nested in value:
                    yield from strings(nested)

        text = " ".join(strings(payload)).lower().replace("_", " ").replace("-", " ")
        return ("language" in text or "locale" in text) and (
            "unsupported" in text or "not supported" in text or "unavailable" in text
        )

    @staticmethod
    def _language_candidates(requested: str, configured: str) -> tuple[str, ...]:
        candidates: list[str] = []
        for value in (
            requested,
            requested.split("-", 1)[0],
            configured,
            configured.split("-", 1)[0],
        ):
            normalized = value.strip()
            if normalized and normalized not in candidates:
                candidates.append(normalized)
        return tuple(candidates or ("zh-CN",))

    async def usage(self) -> DigitalHumanUsageResponse:
        return await self._repository.usage()

    def metrics(self) -> DigitalHumanMetricsResponse:
        average = (
            self._metrics.synthesis_total_ms / self._metrics.synthesis_attempts
            if self._metrics.synthesis_attempts
            else 0
        )
        return DigitalHumanMetricsResponse(
            collected_at=self._clock(),
            tasks_queued=self._metrics.tasks_queued,
            tasks_succeeded=self._metrics.tasks_succeeded,
            tasks_failed=self._metrics.tasks_failed,
            tasks_cancelled=self._metrics.tasks_cancelled,
            cache_hits=self._metrics.cache_hits,
            synthesis_attempts=self._metrics.synthesis_attempts,
            synthesis_failures=self._metrics.synthesis_failures,
            synthesis_total_ms=self._metrics.synthesis_total_ms,
            average_synthesis_ms=average,
        )

    async def metrics_snapshot(self) -> DigitalHumanMetricsResponse:
        """Return persisted daily counters and cross-process synthesis timing data."""
        persisted = await self._repository.metrics_snapshot(self._clock())
        attempts = int(persisted["synthesis_attempts"])
        total_ms = float(persisted["synthesis_total_ms"])
        return DigitalHumanMetricsResponse(
            collected_at=self._clock(),
            tasks_queued=persisted["tasks_queued"],
            tasks_succeeded=persisted["tasks_succeeded"],
            tasks_failed=persisted["tasks_failed"],
            tasks_cancelled=persisted["tasks_cancelled"],
            cache_hits=persisted["cache_hits"],
            synthesis_attempts=attempts,
            synthesis_failures=persisted["synthesis_failures"],
            synthesis_total_ms=total_ms,
            average_synthesis_ms=total_ms / attempts if attempts else 0,
        )

    async def clear_cache(self, provider_id: str | None = None) -> DigitalHumanCacheClearResponse:
        asset_ids = await self._repository.detach_cached_tasks(provider_id)
        deleted = 0
        if self._asset_service is not None:
            for asset_id in set(asset_ids):
                try:
                    if await self._asset_service.references(asset_id):
                        continue
                    await self._asset_service.delete(asset_id)
                    deleted += 1
                except (AssetInUse, AssetNotFound):
                    continue
        return DigitalHumanCacheClearResponse(
            detached_task_count=len(asset_ids), deleted_asset_count=deleted
        )

    async def provider_health(
        self, provider_id: str, *, limit: int = 50
    ) -> tuple[DigitalHumanProviderHealthResponse, ...]:
        return await self._repository.provider_health(provider_id, limit=limit)

    async def cost_report(
        self, *, period_start: datetime, period_end: datetime
    ) -> DigitalHumanCostReportResponse:
        return await self._repository.cost_report(period_start=period_start, period_end=period_end)

    async def list_audit(self, *, limit: int = 100) -> tuple[DigitalHumanAuditResponse, ...]:
        return await self._repository.list_audit(limit=limit)

    async def draft(self, data: SpeechDraftRequest) -> SpeechDraftResponse:
        started = time.perf_counter()
        try:
            audit_settings = await self._repository.get_settings()
            audit_model = audit_settings.ai_model or "gateway-default"
        except Exception:
            audit_model = "unknown"
        try:
            result = await self._draft(data)
        except Exception as error:
            try:
                await self._repository.record_audit_event(
                    action="speech.ai_draft_failed",
                    resource_type="ai_draft",
                    resource_id=data.operation,
                    details={
                        "operation": data.operation,
                        "stage": self._draft_failure_stage(error),
                        "model": audit_model,
                        "error_code": (
                            error.args[0]
                            if isinstance(error, SpeechProviderUnavailable) and error.args
                            else getattr(error, "code", None) or "SPEECH_AI_DRAFT_FAILED"
                        ),
                        "duration_ms": str(round((time.perf_counter() - started) * 1000)),
                    },
                )
            except Exception:
                pass
            raise
        try:
            await self._repository.record_audit_event(
                action="speech.ai_draft_succeeded",
                resource_type="ai_draft",
                resource_id=data.operation,
                details={
                    "operation": data.operation,
                    "stage": "complete",
                    "model": audit_model,
                    "duration_ms": str(round((time.perf_counter() - started) * 1000)),
                },
            )
        except Exception:
            pass
        return result

    @staticmethod
    def _draft_failure_stage(error: Exception) -> str:
        code = (
            error.args[0]
            if isinstance(error, SpeechProviderUnavailable) and error.args
            else getattr(error, "code", "") or ""
        )
        if "CONTEXT" in code:
            return "context"
        if "VARIABLE" in code or "CONTENT" in code or "INVALID" in code:
            return "output_validation"
        if "AI" in code or "GATEWAY" in code or "PROVIDER" in code:
            return "gateway"
        return "validation"

    async def _draft(self, data: SpeechDraftRequest) -> SpeechDraftResponse:
        settings = await self._repository.get_settings()
        if not settings.ai_enabled:
            raise SpeechProviderUnavailable("SPEECH_AI_DISABLED")
        if self._ai_gateway is None:
            raise SpeechProviderUnavailable("SPEECH_AI_NOT_CONFIGURED")
        if len(data.allowed_variables) > settings.ai_context_limit:
            raise SpeechProviderUnavailable("SPEECH_DRAFT_CONTEXT_LIMIT")
        if data.operation == "generate" and not data.allowed_variables:
            raise SpeechProviderUnavailable("SPEECH_DRAFT_CONTEXT_REQUIRED")
        variables = ", ".join(data.allowed_variables)
        system = (
            "You write short dashboard narration for a digital human. Return JSON with keys "
            "text and warnings. Keep text <= 4000 characters. Use only the supplied variable "
            "names with {{name}} syntax; never invent SQL, HTML, scripts, secrets, or values."
        )
        user = (
            f"operation={data.operation}\nlanguage={data.language}\ntone={data.tone}\n"
            f"allowed_variables={variables}\nsource_text={data.source_text.strip()}"
        )
        result = await self._ai_gateway.complete_json(
            system=system,
            user=user,
            response_model=SpeechDraftResponse,
            **({"model": settings.ai_model} if settings.ai_model else {}),
        )
        try:
            placeholders = parse_speech_template(result.text)
        except ValueError as error:
            raise SpeechProviderUnavailable("SPEECH_DRAFT_INVALID") from error
        allowed = set(data.allowed_variables)
        if any(
            token.name not in allowed or sensitive_speech_field(token.name)
            for token in placeholders
        ):
            raise SpeechProviderUnavailable("SPEECH_DRAFT_VARIABLE_DENIED")
        if re.search(
            r"(?i)<\s*script|javascript\s*:|\b(?:drop|delete)\s+table\b|(?:api[_-]?key|password|secret|token)\s*=",
            result.text,
        ):
            raise SpeechProviderUnavailable("SPEECH_DRAFT_CONTENT_DENIED")
        self._validate_governed_text(result.text, settings)
        return result

    @staticmethod
    def _validate_governed_text(text: str, settings: DigitalHumanSettingsResponse) -> None:
        normalized = text.casefold()
        if any(word.casefold() in normalized for word in settings.forbidden_words):
            raise SpeechProviderUnavailable("SPEECH_CONTENT_FORBIDDEN_WORD")
        for pattern in settings.sensitive_patterns:
            try:
                matched = re.search(pattern, text, flags=re.IGNORECASE)
            except re.error as error:
                raise SpeechProviderUnavailable("SPEECH_GOVERNANCE_PATTERN_INVALID") from error
            if matched:
                raise SpeechProviderUnavailable("SPEECH_CONTENT_SENSITIVE_PATTERN")
