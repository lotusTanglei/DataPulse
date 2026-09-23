from __future__ import annotations

import asyncio
import json
from pathlib import Path

from pydantic import Field, ValidationError

from datapulse.ai.context import DatasetContextService
from datapulse.ai.edit import apply_ai_edit_commands, validate_edit_document
from datapulse.ai.gateway import AiGateway
from datapulse.ai.models import AiAnalysisError, AiGatewayError, AiHealth
from datapulse.ai.plan_generator import ScreenPlanGenerator
from datapulse.contracts.ai import (
    AiAnalysisDraft,
    AiAnalysisRequest,
    AiAnalysisResponse,
    AiChartRequest,
    AiChartResponse,
    AiEditCommand,
    AiEditRequest,
    AiEditResponse,
    AiScreenEditRequest,
    AiScreenEditResponse,
    AiScreenRequest,
    AiScreenResponse,
)
from datapulse.contracts.chart import Aggregation, ChartSpec, ChartType, FilterOperator
from datapulse.contracts.common import ContractModel, JsonValue, NonBlankStr
from datapulse.contracts.dashboard_plan import DashboardPlan
from datapulse.contracts.dataset import FileQuery, RestQuery, SqlQuery
from datapulse.dataset.models import DatasetResponse
from datapulse.dataset.repository import (
    DatasetDefinitionInvalid,
    DatasetNotFound,
    DatasetRepository,
)
from datapulse.datasource.registry import ConnectorRegistry
from datapulse.datasource.repository import DatasourceNotFound
from datapulse.datasource.service import DatasourceService
from datapulse.errors import DataPulseError
from datapulse.filedata.duckdb_executor import FileQueryExecutionError
from datapulse.filedata.parsers import FileParseInvalid, parse_file
from datapulse.filedata.query import FileDatasetQueryService
from datapulse.filedata.repository import FileAssetNotFound, FileAssetRepository
from datapulse.query.execution import QueryExecutionError
from datapulse.query.models import QueryResult
from datapulse.query.parameters import ParameterValidationError
from datapulse.query.safety import QueryValidationError
from datapulse.screen.chart_query import ChartQueryCompiler, ChartQueryInvalid
from datapulse.screen.models import (
    DashboardPlanCompileRequest,
    DashboardPlanRecompileRequest,
)
from datapulse.screen.planning import PlanValidationError
from datapulse.screen.planning_service import DashboardPlanningService


class _AiChartDraftResponse(ContractModel):
    chart_spec: dict[str, JsonValue]
    explanation: NonBlankStr
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class _AiEditDraftResponse(ContractModel):
    commands: tuple[AiEditCommand, ...] = Field(min_length=1, max_length=8)
    explanation: NonBlankStr
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class _AiScreenEditDraftResponse(ContractModel):
    plan: DashboardPlan
    affected_region_ids: tuple[NonBlankStr, ...] = Field(min_length=1, max_length=12)
    explanation: NonBlankStr
    warnings: tuple[str, ...] = Field(default_factory=tuple)


_VISUAL_CAPABILITIES: dict[ChartType, str] = {
    ChartType.AREA: "at least 1 dimension and at least 1 measure",
    ChartType.BAR: "at least 1 dimension and at least 1 measure",
    ChartType.FUNNEL: "at least 1 dimension and at least 1 measure",
    ChartType.GAUGE: "0 or 1 dimension and exactly 1 measure",
    ChartType.HEATMAP: "at least 1 dimension and at least 1 measure",
    ChartType.KPI: "0 or 1 dimension and exactly 1 measure",
    ChartType.LINE: "at least 1 dimension and at least 1 measure",
    ChartType.MAP: "exactly 1 dimension and at least 1 measure",
    ChartType.PIE: "exactly 1 dimension and at least 1 measure",
    ChartType.PROGRESS: "0 or 1 dimension and exactly 1 measure",
    ChartType.RADAR: "at least 1 dimension and at least 1 measure",
    ChartType.SCATTER: "at least 1 dimension and at least 1 measure",
    ChartType.TABLE: "at least 1 selected dimension or measure",
}


class AiService:
    def __init__(
        self,
        *,
        gateway: AiGateway,
        context_service: DatasetContextService | None = None,
        dataset_repository: DatasetRepository | None = None,
        datasource_service: DatasourceService | None = None,
        registry: ConnectorRegistry | None = None,
        file_asset_repository: FileAssetRepository | None = None,
        file_query_service: FileDatasetQueryService | None = None,
        planning_service: DashboardPlanningService | None = None,
        max_context_rows: int = 100,
        screen_timeout_seconds: int = 120,
    ) -> None:
        self._gateway = gateway
        self._context_service = context_service
        self._dataset_repository = dataset_repository
        self._datasource_service = datasource_service
        self._registry = registry
        self._file_asset_repository = file_asset_repository
        self._file_query_service = file_query_service
        self._planning_service = planning_service or (
            DashboardPlanningService(dataset_repository=dataset_repository)
            if dataset_repository is not None
            else None
        )
        self._compiler = ChartQueryCompiler()
        self._max_context_rows = max_context_rows
        self._screen_timeout_seconds = screen_timeout_seconds

    def health(self) -> AiHealth:
        return self._gateway.health()

    async def _dataset(self, dataset_id: str) -> DatasetResponse:
        if self._dataset_repository is None:
            raise RuntimeError("dataset repository is not configured")
        try:
            return await self._dataset_repository.get(dataset_id)
        except (DatasetNotFound, DatasetDefinitionInvalid) as error:
            raise AiAnalysisError("AI_DATASET_INVALID", "The dataset is invalid.") from error

    def _default_limit(self, dataset: DatasetResponse) -> int:
        return min(1000, dataset.definition.max_rows)

    async def _contexts(
        self,
        dataset_ids: tuple[str, ...],
        *,
        question: str | None = None,
    ) -> tuple[object, ...]:
        if self._context_service is None:
            raise RuntimeError("context service is not configured")
        try:
            return await self._context_service.build(
                dataset_ids,
                max_rows=self._max_context_rows,
                question=question,
            )
        except (
            DatasetNotFound,
            DatasetDefinitionInvalid,
            DatasourceNotFound,
            FileAssetNotFound,
            FileParseInvalid,
            QueryValidationError,
            ParameterValidationError,
            QueryExecutionError,
            FileQueryExecutionError,
            DataPulseError,
        ) as error:
            raise AiAnalysisError("AI_DATASET_INVALID", "The dataset is invalid.") from error

    def _chart_spec(
        self,
        *,
        response: AiAnalysisDraft,
        dataset: DatasetResponse,
    ) -> ChartSpec:
        spec = response.chart_spec or ChartSpec(
            dataset_id=dataset.id,
            dimensions=response.plan.dimensions,
            measures=response.plan.measures,
            filters=response.plan.filters,
            sort=response.plan.sort,
            limit=min(dataset.definition.max_rows, self._max_context_rows),
            visual={"type": response.plan.recommended_chart},
        )
        if spec.dataset_id != dataset.id:
            raise AiAnalysisError("AI_DATASET_INVALID", "The dataset is invalid.")
        return spec

    def _normalize_chart_spec(
        self,
        *,
        payload: dict[str, JsonValue],
        dataset: DatasetResponse,
        target_component_type: ChartType | None = None,
    ) -> ChartSpec:
        normalized = dict(payload)
        normalized["dataset_id"] = dataset.id
        normalized.setdefault("limit", self._default_limit(dataset))
        try:
            spec = ChartSpec.model_validate(normalized)
        except (TypeError, ValueError, ValidationError) as error:
            raise AiAnalysisError("AI_CHART_INVALID", "The chart is invalid.") from error
        if target_component_type is not None and spec.visual.type is not target_component_type:
            raise AiAnalysisError("AI_CHART_INVALID", "The chart is invalid.")
        return spec

    def _chart_generation_prompt(
        self,
        *,
        request: AiChartRequest,
        dataset: DatasetResponse,
        contexts: tuple[object, ...],
        request_id: str,
    ) -> tuple[str, str]:
        fields = ", ".join(
            f"{field.name}:{field.data_type.value}" for field in dataset.definition.fields
        )
        capabilities = "; ".join(
            f"{chart_type.value}={rule}" for chart_type, rule in _VISUAL_CAPABILITIES.items()
        )
        target_component_type = (
            request.target_component_type.value
            if request.target_component_type is not None
            else "any"
        )
        serialized_contexts = json.dumps(
            [item.model_dump(mode="json") for item in contexts],
            ensure_ascii=False,
        )
        system = (
            "You are a DataPulse chart assistant. "
            "Return only valid JSON for the response model. "
            "Use only the provided dataset fields, supported aggregations, "
            "supported filter operators, and chart capabilities."
        )
        user = (
            f"request_id: {request_id}\n"
            f"dataset_id: {request.dataset_id}\n"
            f"question: {request.question}\n"
            f"target_component_type: {target_component_type}\n"
            f"allowed_fields: {fields}\n"
            f"allowed_aggregations: {', '.join(item.value for item in Aggregation)}\n"
            f"allowed_filter_operators: {', '.join(item.value for item in FilterOperator)}\n"
            f"visual_capabilities: {capabilities}\n"
            "rules: do not invent fields; do not emit SQL; do not exceed limit 5000; "
            "chart_spec must omit dataset_id because the server will inject it.\n"
            f"contexts: {serialized_contexts}"
        )
        return system, user

    async def _preview_sql(
        self,
        *,
        dataset: DatasetResponse,
        chart_spec: ChartSpec,
        request_id: str,
        trigger: str,
    ) -> QueryResult:
        if self._datasource_service is None or self._registry is None:
            raise RuntimeError("sql dataset services are not configured")
        source = await self._datasource_service.get(dataset.data_source_id)
        self._registry.get(source.config.type)
        request = self._compiler.compile(chart_spec, dataset.definition, {})
        return await self._datasource_service.query(
            dataset.data_source_id,
            request,
            request_id=request_id,
            dataset_id=dataset.id,
            trigger=trigger,
        )

    async def _preview_file(
        self,
        *,
        dataset: DatasetResponse,
        chart_spec: ChartSpec,
        request_id: str,
        trigger: str,
    ) -> QueryResult:
        if self._file_asset_repository is None or self._file_query_service is None:
            raise RuntimeError("file dataset services are not configured")
        query = dataset.definition.query
        if not isinstance(query, FileQuery):
            raise AiAnalysisError("AI_CHART_INVALID", "The chart is invalid.")
        asset = await self._file_asset_repository.get(query.asset_id)
        parsed = await parse_file(
            Path(asset.storage_path),
            query.format,
            sheet_name=query.sheet_name,
            max_rows=min(self._max_context_rows, dataset.definition.max_rows),
        )
        return await self._file_query_service.query(
            dataset=dataset.definition,
            chart_spec=chart_spec,
            parameters={},
            request_id=request_id,
            source_path=parsed.normalized_path,
        )

    async def _preview_rest(
        self,
        *,
        dataset: DatasetResponse,
        request_id: str,
    ) -> QueryResult:
        if self._datasource_service is None:
            raise RuntimeError("REST dataset services are not configured")
        query = dataset.definition.query
        if not isinstance(query, RestQuery):
            raise AiAnalysisError("AI_CHART_INVALID", "The chart is invalid.")
        return await self._datasource_service.rest_query(
            dataset.data_source_id,
            query,
            parameters={
                parameter.name: parameter.default for parameter in dataset.definition.parameters
            },
            max_rows=self._default_limit(dataset),
            timeout_seconds=dataset.definition.timeout_seconds,
            request_id=request_id,
        )

    async def _validate_and_preview(
        self,
        *,
        dataset: DatasetResponse,
        chart_spec: ChartSpec,
        request_id: str,
        trigger: str,
    ) -> QueryResult:
        try:
            if isinstance(dataset.definition.query, SqlQuery):
                return await self._preview_sql(
                    dataset=dataset,
                    chart_spec=chart_spec,
                    request_id=request_id,
                    trigger=trigger,
                )
            if isinstance(dataset.definition.query, FileQuery):
                return await self._preview_file(
                    dataset=dataset,
                    chart_spec=chart_spec,
                    request_id=request_id,
                    trigger=trigger,
                )
            if isinstance(dataset.definition.query, RestQuery):
                return await self._preview_rest(
                    dataset=dataset,
                    request_id=request_id,
                )
            raise AiAnalysisError("AI_CHART_INVALID", "The chart is invalid.")
        except (
            ChartQueryInvalid,
            QueryValidationError,
            ParameterValidationError,
            QueryExecutionError,
            FileQueryExecutionError,
            FileParseInvalid,
            DataPulseError,
        ) as error:
            raise AiAnalysisError("AI_CHART_INVALID", "The chart is invalid.") from error
        except (
            DatasourceNotFound,
            FileAssetNotFound,
            DatasetNotFound,
            DatasetDefinitionInvalid,
        ) as error:
            raise AiAnalysisError("AI_DATASET_INVALID", "The dataset is invalid.") from error

    async def analyze(
        self,
        request: AiAnalysisRequest,
        *,
        request_id: str,
    ) -> AiAnalysisResponse:
        if self._context_service is None:
            raise RuntimeError("context service is not configured")
        self._gateway.ensure_configured()
        datasets = tuple([await self._dataset(dataset_id) for dataset_id in request.dataset_ids])
        contexts = await self._contexts(request.dataset_ids, question=request.question)
        system = (
            "You are a DataPulse analytics assistant. "
            "Return only valid JSON that matches the requested response model."
        )
        serialized_contexts = json.dumps(
            [item.model_dump(mode="json") for item in contexts],
            ensure_ascii=False,
        )
        user = (
            f"request_id: {request_id}\n"
            f"mode: {request.mode}\n"
            f"dataset_ids: {', '.join(request.dataset_ids)}\n"
            f"question: {request.question}\n"
            f"contexts: {serialized_contexts}"
        )
        response = await self._gateway.complete_json(
            system=system,
            user=user,
            response_model=AiAnalysisDraft,
        )
        if not response.plan.dataset_ids or any(
            dataset_id not in request.dataset_ids for dataset_id in response.plan.dataset_ids
        ):
            raise AiAnalysisError("AI_DATASET_INVALID", "The dataset is invalid.")

        datasets_by_id = {dataset.id: dataset for dataset in datasets}
        dataset = datasets_by_id[response.plan.dataset_ids[0]]
        chart_spec = self._chart_spec(response=response, dataset=dataset)
        preview = await self._validate_and_preview(
            dataset=dataset,
            chart_spec=chart_spec,
            request_id=request_id,
            trigger="ai-analyze",
        )
        return AiAnalysisResponse.model_validate(
            {
                **response.model_dump(mode="json"),
                "chart_spec": chart_spec,
                "preview": preview,
            }
        )

    async def generate_chart(
        self,
        request: AiChartRequest,
        *,
        request_id: str,
    ) -> AiChartResponse:
        if self._context_service is None:
            raise RuntimeError("context service is not configured")
        self._gateway.ensure_configured()
        dataset = await self._dataset(request.dataset_id)
        contexts = await self._contexts((request.dataset_id,), question=request.question)
        system, user = self._chart_generation_prompt(
            request=request,
            dataset=dataset,
            contexts=contexts,
            request_id=request_id,
        )
        response = await self._gateway.complete_json(
            system=system,
            user=user,
            response_model=_AiChartDraftResponse,
        )
        chart_spec = self._normalize_chart_spec(
            payload=response.chart_spec,
            dataset=dataset,
            target_component_type=request.target_component_type,
        )
        preview = await self._validate_and_preview(
            dataset=dataset,
            chart_spec=chart_spec,
            request_id=request_id,
            trigger="ai-chart",
        )
        return AiChartResponse(
            chart_spec=chart_spec,
            explanation=response.explanation,
            preview=preview,
            warnings=response.warnings,
        )

    async def generate_screen(
        self,
        request: AiScreenRequest,
        *,
        request_id: str,
    ) -> AiScreenResponse:
        self._gateway.ensure_configured()
        if self._context_service is None or self._dataset_repository is None:
            raise RuntimeError("screen generation services are not configured")
        generator = ScreenPlanGenerator(
            gateway=self._gateway,
            context_service=self._context_service,
            dataset_repository=self._dataset_repository,
            max_context_rows=self._max_context_rows,
        )
        try:
            async with asyncio.timeout(self._screen_timeout_seconds):
                draft = await generator.generate(request, request_id=request_id)
                if self._planning_service is None:
                    raise RuntimeError("screen planning service is not configured")
                compiled = await self._planning_service.compile(
                    DashboardPlanCompileRequest(
                        plan=draft.plan,
                        canvas_width=request.canvas_width,
                        canvas_height=request.canvas_height,
                    ),
                    request_id=request_id,
                )
                return AiScreenResponse(
                    plan=draft.plan,
                    document=compiled.document,
                    report=compiled.report,
                    explanation=draft.explanation,
                    warnings=tuple(dict.fromkeys((*draft.warnings, *compiled.warnings))),
                )
        except TimeoutError as error:
            raise AiGatewayError("AI_TIMEOUT", "AI screen generation timed out.") from error
        except (
            DatasetNotFound,
            DatasetDefinitionInvalid,
            DatasourceNotFound,
            FileAssetNotFound,
            FileParseInvalid,
            QueryValidationError,
            ParameterValidationError,
            QueryExecutionError,
            FileQueryExecutionError,
        ) as error:
            raise AiAnalysisError("AI_DATASET_INVALID", "The dataset is invalid.") from error

    def _screen_edit_prompt(
        self,
        *,
        request: AiScreenEditRequest,
        contexts: tuple[object, ...],
        request_id: str,
    ) -> tuple[str, str]:
        requested_regions = request.affected_region_ids or tuple(
            region.id for region in request.plan.regions
        )
        system = (
            "You are a DataPulse dashboard planning assistant. Return only valid JSON for "
            "the response model. Modify the DashboardPlan, never pixel coordinates. Use one "
            "dataset per widget; never publish, join datasets, execute code, or emit SQL."
        )
        user = (
            f"request_id: {request_id}\n"
            f"question: {request.question}\n"
            f"requested_region_ids: {', '.join(requested_regions)}\n"
            "allowed_changes: visual style, chart type, anomaly emphasis, and region planning.\n"
            "rules: return the complete updated plan and the exact affected_region_ids; "
            "preserve every unselected region; use only existing dataset IDs and fields; "
            "keep every widget bound to one scalar dataset_id; do not include frame, x, y, "
            "width, height, scripts, SQL, URLs, or publish commands.\n"
            f"plan: {json.dumps(request.plan.model_dump(mode='json'), ensure_ascii=False)}\n"
            "document: "
            f"{json.dumps(request.document.model_dump(mode='json'), ensure_ascii=False)}\n"
            "contexts: "
            f"{json.dumps([item.model_dump(mode='json') for item in contexts], ensure_ascii=False)}"
        )
        return system, user

    async def edit_screen(
        self,
        request: AiScreenEditRequest,
        *,
        request_id: str,
    ) -> AiScreenEditResponse:
        self._gateway.ensure_configured()
        if self._planning_service is None:
            raise RuntimeError("screen planning service is not configured")
        known_regions = {region.id for region in request.plan.regions}
        if not set(request.affected_region_ids) <= known_regions:
            raise AiAnalysisError(
                "AI_SCREEN_EDIT_INVALID",
                "The requested region scope is invalid.",
            )
        try:
            async with asyncio.timeout(self._screen_timeout_seconds):
                contexts = await self._contexts(
                    request.plan.dataset_ids,
                    question=request.question,
                )
                system, user = self._screen_edit_prompt(
                    request=request,
                    contexts=contexts,
                    request_id=request_id,
                )
                draft = await self._gateway.complete_json(
                    system=system,
                    user=user,
                    response_model=_AiScreenEditDraftResponse,
                )
                if not set(draft.plan.dataset_ids) <= set(request.plan.dataset_ids):
                    raise AiAnalysisError(
                        "AI_DATASET_INVALID",
                        "The edited plan references another dataset.",
                    )
                affected_region_ids = tuple(dict.fromkeys(draft.affected_region_ids))
                if request.affected_region_ids and set(affected_region_ids) != set(
                    request.affected_region_ids
                ):
                    raise AiAnalysisError(
                        "AI_SCREEN_EDIT_INVALID",
                        "The edited plan changed regions outside the requested scope.",
                    )
                if not set(affected_region_ids) <= {
                    *(region.id for region in request.plan.regions),
                    *(region.id for region in draft.plan.regions),
                }:
                    raise AiAnalysisError(
                        "AI_SCREEN_EDIT_INVALID",
                        "The edited plan returned an unknown region.",
                    )
                compiled = await self._planning_service.recompile(
                    DashboardPlanRecompileRequest(
                        previous_plan=request.plan,
                        plan=draft.plan,
                        document=request.document,
                        affected_region_ids=affected_region_ids,
                    ),
                    request_id=request_id,
                )
                if compiled.report is None:
                    raise RuntimeError("screen planning preflight is not configured")
                return AiScreenEditResponse(
                    plan=compiled.plan,
                    document=compiled.document,
                    affected_region_ids=compiled.affected_region_ids,
                    report=compiled.report,
                    explanation=draft.explanation,
                    warnings=tuple(dict.fromkeys((*draft.warnings, *compiled.warnings))),
                )
        except TimeoutError as error:
            raise AiGatewayError("AI_TIMEOUT", "AI screen editing timed out.") from error
        except PlanValidationError as error:
            raise AiAnalysisError(
                "AI_SCREEN_EDIT_INVALID",
                "The screen edit is invalid.",
                issues=tuple(
                    {
                        "component_id": issue.widget_id or "plan",
                        "field": issue.field,
                        "reason": issue.reason,
                        "expected": issue.expected,
                    }
                    for issue in error.result.issues
                ),
            ) from error

    @staticmethod
    def _document_dataset_ids(request: AiEditRequest) -> tuple[str, ...]:
        ids: list[str] = list(request.dataset_ids)
        for component in request.document.components:
            binding = component.data_binding or {}
            chart_spec = binding.get("chart_spec")
            if isinstance(chart_spec, dict):
                dataset_id = chart_spec.get("dataset_id")
                if isinstance(dataset_id, str) and dataset_id.strip():
                    ids.append(dataset_id)
        return tuple(dict.fromkeys(ids))

    @staticmethod
    def _command_component_ids(command: AiEditCommand) -> tuple[str, ...]:
        if hasattr(command, "component_id"):
            return (command.component_id,)
        return tuple(command.component_ids)

    def _edit_prompt(
        self,
        *,
        request: AiEditRequest,
        dataset_ids: tuple[str, ...],
        contexts: tuple[object, ...],
        request_id: str,
    ) -> tuple[str, str]:
        document = request.document.model_dump(mode="json")
        selected = set(request.selected_component_ids)
        selected_components = [
            component
            for component in document["components"]
            if isinstance(component, dict) and component.get("id") in selected
        ]
        serialized_contexts = json.dumps(
            [item.model_dump(mode="json") for item in contexts],
            ensure_ascii=False,
        )
        system = (
            "You are a DataPulse editor assistant. Return only valid JSON for the "
            "response model. Generate safe, minimal edit commands for the selected "
            "components; never publish, execute code, emit SQL, or invent fields."
        )
        user = (
            f"request_id: {request_id}\n"
            f"question: {request.question}\n"
            f"selected_component_ids: {', '.join(request.selected_component_ids)}\n"
            f"dataset_ids: {', '.join(dataset_ids) or 'none'}\n"
            "allowed_command_types: update_frame, update_props, update_style, "
            "update_data_binding, set_component_state\n"
            "rules: only target selected components; use one to eight minimal commands; "
            "update_props only changes supported visible properties; update_data_binding "
            "must contain a validated chart_spec; keep every frame inside the canvas; "
            "never return publish, script, url, path, sql, or external assets.\n"
            f"selected_components: {json.dumps(selected_components, ensure_ascii=False)}\n"
            f"document: {json.dumps(document, ensure_ascii=False)}\n"
            f"contexts: {serialized_contexts}"
        )
        return system, user

    async def generate_edit(
        self,
        request: AiEditRequest,
        *,
        request_id: str,
    ) -> AiEditResponse:
        self._gateway.ensure_configured()
        component_ids = {component.id for component in request.document.components}
        if not set(request.selected_component_ids) <= component_ids:
            raise AiAnalysisError("AI_EDIT_INVALID", "The selected component is invalid.")
        selected_components = {component.id: component for component in request.document.components}
        if any(
            selected_components[component_id].state.locked
            for component_id in request.selected_component_ids
        ):
            raise AiAnalysisError("AI_EDIT_INVALID", "The selected component is locked.")

        dataset_ids = self._document_dataset_ids(request)
        if len(dataset_ids) > 8:
            raise AiAnalysisError("AI_DATASET_INVALID", "Too many datasets are referenced.")
        datasets = tuple([await self._dataset(dataset_id) for dataset_id in dataset_ids])
        contexts = await self._contexts(dataset_ids) if dataset_ids else ()
        system, user = self._edit_prompt(
            request=request,
            dataset_ids=dataset_ids,
            contexts=contexts,
            request_id=request_id,
        )
        response = await self._gateway.complete_json(
            system=system,
            user=user,
            response_model=_AiEditDraftResponse,
        )
        selected = set(request.selected_component_ids)
        if any(
            not set(self._command_component_ids(command)) <= selected
            for command in response.commands
        ):
            raise AiAnalysisError("AI_EDIT_INVALID", "The AI edit targets another component.")
        updated = apply_ai_edit_commands(request.document, response.commands)
        validate_edit_document(updated, {dataset.id: dataset for dataset in datasets})
        return AiEditResponse(
            commands=response.commands,
            explanation=response.explanation,
            warnings=response.warnings,
        )


__all__ = ["AiService"]
