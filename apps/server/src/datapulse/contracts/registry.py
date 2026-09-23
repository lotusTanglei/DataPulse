"""Export registry, loaded only when schema generation or public exports require it."""

from pydantic import BaseModel

from datapulse.contracts.ai import AiEditResponse, AnalysisPlan
from datapulse.contracts.chart import ChartSpec
from datapulse.contracts.dashboard import DashboardDocument
from datapulse.contracts.dashboard_plan import DashboardPlan
from datapulse.contracts.dataset import DatasetDefinition
from datapulse.contracts.digital_human import (
    DigitalHumanAction,
    DigitalHumanBinding,
    DigitalHumanSpec,
    DigitalHumanTrigger,
    SpeechScriptSegment,
)
from datapulse.contracts.embed import EmbedMessageEnvelope, EmbedTicketClaims
from datapulse.contracts.generation import GenerationSelfCheckReport
from datapulse.contracts.plugin import PluginManifest
from datapulse.contracts.screen_asset import (
    ScreenAssetPatch,
    ScreenAssetReference,
    ScreenAssetResponse,
    ScreenAssetUsage,
)
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
from datapulse.ecosystem.models import CatalogPackage, TemplateApply, TemplateManifest
from datapulse.identity.models import (
    AuditResponse,
    GrantRequest,
    ResourceAccessResponse,
    SpeechProviderOption,
    UserCreate,
    UserPatch,
    UserResponse,
)

CONTRACT_MODELS: dict[str, type[BaseModel]] = {
    "analysis-plan": AnalysisPlan,
    "ai-edit-response": AiEditResponse,
    "chart-spec": ChartSpec,
    "dashboard-document": DashboardDocument,
    "dashboard-plan": DashboardPlan,
    "dataset-definition": DatasetDefinition,
    "digital-human-spec": DigitalHumanSpec,
    "digital-human-binding": DigitalHumanBinding,
    "digital-human-trigger": DigitalHumanTrigger,
    "digital-human-action": DigitalHumanAction,
    "speech-script-segment": SpeechScriptSegment,
    "embed-message": EmbedMessageEnvelope,
    "embed-ticket-claims": EmbedTicketClaims,
    "generation-self-check": GenerationSelfCheckReport,
    "plugin-manifest": PluginManifest,
    "screen-asset": ScreenAssetResponse,
    "screen-asset-patch": ScreenAssetPatch,
    "screen-asset-reference": ScreenAssetReference,
    "screen-asset-usage": ScreenAssetUsage,
    "digital-human-provider": DigitalHumanProviderResponse,
    "digital-human-provider-test": DigitalHumanProviderTestResponse,
    "digital-human-provider-health": DigitalHumanProviderHealthResponse,
    "digital-human-cost-report": DigitalHumanCostReportResponse,
    "digital-human-metrics": DigitalHumanMetricsResponse,
    "digital-human-playback-diagnostic": DigitalHumanPlaybackDiagnosticResponse,
    "digital-human-cache-clear": DigitalHumanCacheClearResponse,
    "speech-plan": SpeechPlanResponse,
    "speech-task": SpeechTaskResponse,
    "digital-human-usage": DigitalHumanUsageResponse,
    "digital-human-settings": DigitalHumanSettingsResponse,
    "speech-draft": SpeechDraftResponse,
    "studio-user": UserResponse,
    "studio-user-create": UserCreate,
    "studio-user-patch": UserPatch,
    "resource-grant": GrantRequest,
    "resource-access": ResourceAccessResponse,
    "speech-provider-option": SpeechProviderOption,
    "identity-audit": AuditResponse,
    "catalog-package": CatalogPackage,
    "template-manifest": TemplateManifest,
    "template-apply": TemplateApply,
}

__all__ = [
    "CONTRACT_MODELS",
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
