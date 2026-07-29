"""Versioned public contracts shared by DataPulse subsystems."""

from pydantic import BaseModel

from datapulse.contracts.ai import AnalysisPlan
from datapulse.contracts.chart import ChartSpec
from datapulse.contracts.dashboard import DashboardDocument
from datapulse.contracts.dataset import DatasetDefinition
from datapulse.contracts.embed import EmbedMessageEnvelope, EmbedTicketClaims
from datapulse.contracts.plugin import PluginManifest

CONTRACT_MODELS: dict[str, type[BaseModel]] = {
    "analysis-plan": AnalysisPlan,
    "chart-spec": ChartSpec,
    "dashboard-document": DashboardDocument,
    "dataset-definition": DatasetDefinition,
    "embed-message": EmbedMessageEnvelope,
    "embed-ticket-claims": EmbedTicketClaims,
    "plugin-manifest": PluginManifest,
}

__all__ = ["CONTRACT_MODELS"]
