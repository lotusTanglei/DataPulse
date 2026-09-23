"""Versioned contracts with lazy public exports to avoid import-order cycles."""

from importlib import import_module


def __getattr__(name: str):
    if name.startswith("_"):
        raise AttributeError(name)
    registry = import_module("datapulse.contracts.registry")
    try:
        value = getattr(registry, name)
    except AttributeError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    globals()[name] = value
    return value


__all__ = [
    "CONTRACT_MODELS",
    "DashboardPlan",
    "GenerationSelfCheckReport",
    "DigitalHumanCostReportResponse",
    "DigitalHumanMetricsResponse",
    "DigitalHumanPlaybackDiagnosticResponse",
    "DigitalHumanCacheClearResponse",
    "DigitalHumanAuditResponse",
    "DigitalHumanProviderCreate",
    "DigitalHumanProviderHealthResponse",
    "DigitalHumanProviderResponse",
    "DigitalHumanProviderTestResponse",
    "DigitalHumanProviderUpdate",
    "DigitalHumanSettingsResponse",
    "DigitalHumanSettingsUpdate",
    "DigitalHumanUsageResponse",
    "SpeechDraftRequest",
    "SpeechDraftResponse",
    "SpeechPlanRequest",
    "SpeechPlanResponse",
    "SpeechTaskResponse",
    "SpeechScriptSegment",
]
