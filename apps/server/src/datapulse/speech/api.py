import hmac
from datetime import UTC, datetime
from typing import NoReturn

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import PlainTextResponse

from datapulse.ai.models import AiGatewayError
from datapulse.auth.dependencies import require_admin, require_csrf
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
from datapulse.errors import DataPulseError
from datapulse.identity.models import SpeechProviderOption
from datapulse.speech.repository import (
    SpeechProviderNameConflict,
    SpeechProviderNotFound,
    SpeechTaskNotFound,
)
from datapulse.speech.service import SpeechProviderUnavailable, SpeechQuotaExceeded

router = APIRouter(
    prefix="/api/admin/digital-human", tags=["digital-human"], dependencies=[Depends(require_admin)]
)
internal_router = APIRouter(prefix="/api/internal/digital-human", tags=["internal-digital-human"])


async def require_metrics_token(request: Request) -> None:
    configured = request.app.state.settings.metrics_token
    provided = request.headers.get("Authorization", "")
    expected = f"Bearer {configured}" if configured else ""
    if not configured or not hmac.compare_digest(provided, expected):
        raise DataPulseError(
            code="METRICS_AUTH_REQUIRED",
            message="A valid metrics bearer token is required.",
            status_code=401,
        )


def _prometheus_text(snapshot: DigitalHumanMetricsResponse) -> str:
    labels = 'service="datapulse",feature="digital_human"'
    values = {
        "tasks_queued_total": snapshot.tasks_queued,
        "tasks_succeeded_total": snapshot.tasks_succeeded,
        "tasks_failed_total": snapshot.tasks_failed,
        "tasks_cancelled_total": snapshot.tasks_cancelled,
        "cache_hits_total": snapshot.cache_hits,
        "synthesis_attempts_total": snapshot.synthesis_attempts,
        "synthesis_failures_total": snapshot.synthesis_failures,
        "synthesis_total_ms": snapshot.synthesis_total_ms,
        "average_synthesis_ms": snapshot.average_synthesis_ms,
    }
    lines: list[str] = []
    for metric, value in values.items():
        name = f"datapulse_digital_human_speech_{metric}"
        kind = "counter" if metric.endswith("_total") else "gauge"
        lines.extend(
            [
                f"# HELP {name} Current UTC-day digital human speech metric.",
                f"# TYPE {name} {kind}",
                f"{name}{{{labels}}} {value}",
            ]
        )
    return "\n".join(lines) + "\n"


def _raise(error: Exception) -> NoReturn:
    if isinstance(error, SpeechProviderNotFound):
        raise DataPulseError(
            code="SPEECH_PROVIDER_NOT_FOUND",
            message="The speech provider does not exist.",
            status_code=404,
        ) from error
    if isinstance(error, SpeechTaskNotFound):
        raise DataPulseError(
            code="SPEECH_TASK_NOT_FOUND",
            message="The speech task does not exist.",
            status_code=404,
        ) from error
    if isinstance(error, SpeechProviderNameConflict):
        raise DataPulseError(
            code="SPEECH_PROVIDER_NAME_CONFLICT",
            message="A speech provider with this name already exists.",
            status_code=409,
        ) from error
    if isinstance(error, SpeechProviderUnavailable):
        status = (
            422
            if error.args
            and error.args[0]
            in {
                "SPEECH_DRAFT_CONTEXT_REQUIRED",
                "SPEECH_CONTENT_FORBIDDEN_WORD",
                "SPEECH_CONTENT_SENSITIVE_PATTERN",
                "SPEECH_DRAFT_VARIABLE_DENIED",
                "SPEECH_DRAFT_CONTENT_DENIED",
                "SPEECH_MANUAL_REVIEW_REQUIRED",
            }
            else 503
        )
        raise DataPulseError(
            code=error.args[0] if error.args else error.code,
            message="The speech preview cannot be generated.",
            status_code=status,
        ) from error
    if isinstance(error, SpeechQuotaExceeded):
        raise DataPulseError(
            code=error.args[0] if error.args else error.code,
            message="The digital human speech quota has been reached.",
            status_code=429,
        ) from error
    if isinstance(error, AiGatewayError):
        raise DataPulseError(
            code=error.code, message="The AI speech preview is unavailable.", status_code=503
        ) from error
    raise error


@router.get("/providers")
async def list_providers(request: Request) -> tuple[DigitalHumanProviderResponse, ...]:
    return await request.app.state.speech_service.list_providers()


@router.get("/settings")
async def get_settings(request: Request) -> DigitalHumanSettingsResponse:
    return await request.app.state.speech_service.get_settings()


@router.patch("/settings", dependencies=[Depends(require_csrf)])
async def update_settings(
    payload: DigitalHumanSettingsUpdate, request: Request
) -> DigitalHumanSettingsResponse:
    return await request.app.state.speech_service.update_settings(payload)


@router.post("/providers", status_code=201, dependencies=[Depends(require_csrf)])
async def create_provider(
    payload: DigitalHumanProviderCreate, request: Request
) -> DigitalHumanProviderResponse:
    try:
        return await request.app.state.speech_service.create_provider(payload)
    except (SpeechProviderNameConflict, SpeechProviderUnavailable) as error:
        _raise(error)


@router.patch("/providers/{provider_id}", dependencies=[Depends(require_csrf)])
async def update_provider(
    provider_id: str, payload: DigitalHumanProviderUpdate, request: Request
) -> DigitalHumanProviderResponse:
    try:
        return await request.app.state.speech_service.update_provider(provider_id, payload)
    except (SpeechProviderNotFound, SpeechProviderUnavailable) as error:
        _raise(error)


@router.delete("/providers/{provider_id}", status_code=204, dependencies=[Depends(require_csrf)])
async def delete_provider(provider_id: str, request: Request) -> Response:
    try:
        await request.app.state.speech_service.delete_provider(provider_id)
    except SpeechProviderNotFound as error:
        _raise(error)
    return Response(status_code=204)


@router.post("/providers/{provider_id}/test", dependencies=[Depends(require_csrf)])
async def test_provider(provider_id: str, request: Request) -> DigitalHumanProviderTestResponse:
    try:
        return await request.app.state.speech_service.test_provider(provider_id)
    except SpeechProviderNotFound as error:
        _raise(error)


@router.get("/providers/{provider_id}/health")
async def provider_health(
    provider_id: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
) -> tuple[DigitalHumanProviderHealthResponse, ...]:
    try:
        return await request.app.state.speech_service.provider_health(provider_id, limit=limit)
    except SpeechProviderNotFound as error:
        _raise(error)


@router.post("/plans/preview", dependencies=[Depends(require_csrf)])
async def preview_plan(payload: SpeechPlanRequest, request: Request) -> SpeechPlanResponse:
    try:
        result = await request.app.state.speech_service.create_plan(payload)
        await request.app.state.identity_service.register_owner(
            request.state.admin, "speech_plan", result.id
        )
        return result
    except (SpeechProviderNotFound, SpeechProviderUnavailable) as error:
        _raise(error)


@router.post("/plans/{plan_id}/tasks", status_code=201, dependencies=[Depends(require_csrf)])
async def queue_task(plan_id: str, request: Request) -> SpeechTaskResponse:
    try:
        approved = request.query_params.get("approved", "false").lower() == "true"
        return await request.app.state.speech_service.queue_task_by_id(
            plan_id, approved=approved, request_id=request.state.request_id
        )
    except (SpeechProviderNotFound, SpeechProviderUnavailable, SpeechQuotaExceeded) as error:
        _raise(error)


@router.get("/tasks")
async def list_tasks(
    request: Request,
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> tuple[SpeechTaskResponse, ...]:
    if status is not None and status not in {
        "queued",
        "running",
        "succeeded",
        "failed",
        "cancelled",
    }:
        raise DataPulseError(
            code="SPEECH_TASK_STATUS_INVALID",
            message="The speech task status is invalid.",
            status_code=422,
        )
    return await request.app.state.speech_service.list_tasks(status=status, limit=limit)


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, request: Request) -> SpeechTaskResponse:
    try:
        await request.app.state.identity_service.authorize_speech_asset(
            request.state.admin, task_id, request.state.request_id
        )
        return await request.app.state.speech_service.get_task(task_id)
    except SpeechTaskNotFound as error:
        _raise(error)


@router.get("/diagnostics")
async def playback_diagnostics(
    request: Request,
    screen_id: str | None = Query(default=None, max_length=128),
    component_id: str | None = Query(default=None, max_length=128),
    limit: int = Query(default=50, ge=1, le=100),
) -> tuple[DigitalHumanPlaybackDiagnosticResponse, ...]:
    return await request.app.state.speech_service.playback_diagnostics(
        screen_id=screen_id,
        component_id=component_id,
        limit=limit,
    )


@router.delete("/tasks/{task_id}", dependencies=[Depends(require_csrf)])
async def cancel_task(task_id: str, request: Request) -> SpeechTaskResponse:
    try:
        return await request.app.state.speech_service.cancel_task(task_id)
    except SpeechTaskNotFound as error:
        _raise(error)


@router.get("/providers/{provider_id}/voices")
async def list_voices(provider_id: str, request: Request) -> tuple[str, ...]:
    try:
        return await request.app.state.speech_service.list_voices(provider_id)
    except (SpeechProviderNotFound, SpeechProviderUnavailable) as error:
        _raise(error)


@router.get("/usage")
async def usage(request: Request) -> DigitalHumanUsageResponse:
    return await request.app.state.speech_service.usage()


@router.get("/metrics")
async def metrics(request: Request) -> DigitalHumanMetricsResponse:
    return await request.app.state.speech_service.metrics_snapshot()


@router.get("/metrics/prometheus", response_class=PlainTextResponse)
async def metrics_prometheus(request: Request) -> PlainTextResponse:
    """Expose low-cardinality speech metrics for a Prometheus-compatible scraper."""
    snapshot = await request.app.state.speech_service.metrics_snapshot()
    return PlainTextResponse(_prometheus_text(snapshot))


@internal_router.get(
    "/metrics/prometheus",
    response_class=PlainTextResponse,
    dependencies=[Depends(require_metrics_token)],
)
async def internal_metrics_prometheus(request: Request) -> PlainTextResponse:
    """Expose the same low-cardinality snapshot to an explicitly authorized scraper."""
    snapshot = await request.app.state.speech_service.metrics_snapshot()
    return PlainTextResponse(_prometheus_text(snapshot))


@router.post("/cache/clear", dependencies=[Depends(require_csrf)])
async def clear_cache(
    request: Request,
    provider_id: str | None = Query(default=None, max_length=36),
) -> DigitalHumanCacheClearResponse:
    return await request.app.state.speech_service.clear_cache(provider_id)


@router.get("/usage/cost")
async def cost_report(
    request: Request,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> DigitalHumanCostReportResponse:
    end = period_end or datetime.now(UTC)
    start = period_start or end.replace(hour=0, minute=0, second=0, microsecond=0)
    if start.tzinfo is None or end.tzinfo is None or start >= end:
        raise DataPulseError(
            code="SPEECH_COST_PERIOD_INVALID",
            message="The cost report period is invalid.",
            status_code=422,
        )
    return await request.app.state.speech_service.cost_report(
        period_start=start.astimezone(UTC), period_end=end.astimezone(UTC)
    )


@router.get("/audit")
async def audit(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
) -> tuple[DigitalHumanAuditResponse, ...]:
    return await request.app.state.speech_service.list_audit(limit=limit)


@router.post("/ai/draft", dependencies=[Depends(require_csrf)])
async def draft(payload: SpeechDraftRequest, request: Request) -> SpeechDraftResponse:
    try:
        return await request.app.state.speech_service.draft(payload)
    except (SpeechProviderUnavailable, AiGatewayError) as error:
        _raise(error)


@router.get("/provider-directory")
async def speech_provider_directory(request: Request) -> tuple[SpeechProviderOption, ...]:
    return await request.app.state.identity_service.speech_provider_directory(request.state.admin)


@router.get("/provider-directory/{provider_id}/voices")
async def speech_provider_voices(provider_id: str, request: Request) -> tuple[str, ...]:
    await request.app.state.identity_service.require_speech_provider(
        request.state.admin, provider_id
    )
    try:
        return await request.app.state.speech_service.list_voices(provider_id)
    except (SpeechProviderNotFound, SpeechProviderUnavailable) as error:
        _raise(error)
