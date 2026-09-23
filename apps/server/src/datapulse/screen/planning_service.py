from __future__ import annotations

from typing import Protocol

from datapulse.contracts.dashboard import DashboardDocument
from datapulse.contracts.dashboard_plan import DashboardPlan
from datapulse.contracts.generation import GenerationSelfCheckReport
from datapulse.dataset.models import DatasetResponse
from datapulse.dataset.repository import DatasetRepository
from datapulse.query.models import QueryResult
from datapulse.screen.compiler import DocumentCompiler
from datapulse.screen.inspection import ExecutionOutcome, GenerationInspector
from datapulse.screen.models import (
    DashboardPlanCompileRequest,
    DashboardPlanCompileResponse,
    DashboardPlanRecompileRequest,
    DashboardPlanRecompileResponse,
)
from datapulse.screen.runtime import ScreenDocumentQueryRequest


class _RuntimeService(Protocol):
    async def query_document_component(
        self,
        data: ScreenDocumentQueryRequest,
        *,
        request_id: str,
    ) -> QueryResult: ...


class DashboardPlanningService:
    def __init__(
        self,
        *,
        dataset_repository: DatasetRepository,
        compiler: DocumentCompiler | None = None,
        runtime_service: _RuntimeService | None = None,
        inspector: GenerationInspector | None = None,
    ) -> None:
        self._dataset_repository = dataset_repository
        self._compiler = compiler or DocumentCompiler()
        self._runtime_service = runtime_service
        self._inspector = inspector or GenerationInspector()

    async def _inspect(
        self,
        *,
        plan: DashboardPlan,
        document: DashboardDocument,
        datasets: tuple[DatasetResponse, ...],
        request_id: str,
    ) -> tuple[
        DashboardDocument,
        GenerationSelfCheckReport | None,
        tuple[str, ...],
    ]:
        if self._runtime_service is None:
            return document, None, ()
        executions: dict[str, ExecutionOutcome] = {}
        for widget in plan.widgets:
            try:
                result = await self._runtime_service.query_document_component(
                    ScreenDocumentQueryRequest(
                        document=document,
                        component_id=widget.id,
                    ),
                    request_id=request_id,
                )
            except Exception as error:
                executions[widget.id] = ExecutionOutcome(
                    status="error",
                    row_count=0,
                    error_code=str(getattr(error, "code", type(error).__name__)),
                )
            else:
                executions[widget.id] = ExecutionOutcome(
                    status="empty" if result.row_count == 0 else "ok",
                    row_count=result.row_count,
                )
        inspected = self._inspector.inspect(
            plan,
            document,
            datasets={dataset.id: dataset.definition for dataset in datasets},
            executions=executions,
        )
        return inspected.document, inspected.report, inspected.warnings

    async def compile(
        self,
        request: DashboardPlanCompileRequest,
        *,
        request_id: str = "plan-compile",
    ) -> DashboardPlanCompileResponse:
        datasets = tuple(
            [
                await self._dataset_repository.get(dataset_id)
                for dataset_id in request.plan.dataset_ids
            ]
        )
        document = self._compiler.compile(
            request.plan,
            datasets={dataset.id: dataset.definition for dataset in datasets},
            authorized_dataset_ids={dataset.id for dataset in datasets},
            canvas_width=request.canvas_width,
            canvas_height=request.canvas_height,
        )
        document, report, warnings = await self._inspect(
            plan=request.plan,
            document=document,
            datasets=datasets,
            request_id=request_id,
        )
        return DashboardPlanCompileResponse(
            plan=request.plan,
            document=document,
            report=report,
            warnings=warnings,
        )

    async def recompile(
        self,
        request: DashboardPlanRecompileRequest,
        *,
        request_id: str = "plan-recompile",
    ) -> DashboardPlanRecompileResponse:
        dataset_ids = tuple(
            dict.fromkeys((*request.previous_plan.dataset_ids, *request.plan.dataset_ids))
        )
        datasets = tuple(
            [await self._dataset_repository.get(dataset_id) for dataset_id in dataset_ids]
        )
        document = self._compiler.recompile_regions(
            previous_plan=request.previous_plan,
            plan=request.plan,
            document=request.document,
            affected_region_ids=set(request.affected_region_ids),
            datasets={dataset.id: dataset.definition for dataset in datasets},
            authorized_dataset_ids=set(request.plan.dataset_ids),
        )
        document, report, warnings = await self._inspect(
            plan=request.plan,
            document=document,
            datasets=datasets,
            request_id=request_id,
        )
        return DashboardPlanRecompileResponse(
            plan=request.plan,
            document=document,
            affected_region_ids=request.affected_region_ids,
            report=report,
            warnings=warnings,
        )


__all__ = ["DashboardPlanningService"]
