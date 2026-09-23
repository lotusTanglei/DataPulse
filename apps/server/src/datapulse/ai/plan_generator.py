from __future__ import annotations

import json

from datapulse.ai.context import DatasetContextService
from datapulse.ai.gateway import AiGateway
from datapulse.ai.models import AiAnalysisError
from datapulse.contracts.ai import AiScreenPlanResponse, AiScreenRequest
from datapulse.contracts.dashboard_plan import DashboardPlan
from datapulse.dataset.models import DatasetResponse
from datapulse.dataset.repository import (
    DatasetDefinitionInvalid,
    DatasetNotFound,
    DatasetRepository,
)
from datapulse.screen.planning import PlanValidationIssue, PlanValidator


def _repair_issue(issue: PlanValidationIssue) -> dict[str, str]:
    return {
        "code": issue.code,
        "component_id": issue.widget_id or "plan",
        "field": issue.field,
        "reason": issue.reason,
        "expected": issue.expected,
    }


class ScreenPlanGenerator:
    def __init__(
        self,
        *,
        gateway: AiGateway,
        context_service: DatasetContextService,
        dataset_repository: DatasetRepository,
        validator: PlanValidator | None = None,
        max_context_rows: int = 100,
    ) -> None:
        self._gateway = gateway
        self._context_service = context_service
        self._dataset_repository = dataset_repository
        self._validator = validator or PlanValidator()
        self._max_context_rows = max_context_rows

    async def _dataset(self, dataset_id: str) -> DatasetResponse:
        try:
            return await self._dataset_repository.get(dataset_id)
        except (DatasetNotFound, DatasetDefinitionInvalid) as error:
            raise AiAnalysisError("AI_DATASET_INVALID", "The dataset is invalid.") from error

    def _prompt(
        self,
        *,
        request: AiScreenRequest,
        datasets: tuple[DatasetResponse, ...],
        contexts: tuple[object, ...],
        request_id: str,
    ) -> tuple[str, str]:
        dataset_description = [
            {
                "dataset_id": dataset.id,
                "name": dataset.name,
                "fields": [
                    {"name": field.name, "data_type": field.data_type.value}
                    for field in dataset.definition.fields
                ],
            }
            for dataset in datasets
        ]
        serialized_contexts = json.dumps(
            [item.model_dump(mode="json") for item in contexts],
            ensure_ascii=False,
        )
        system = (
            "You are a DataPulse dashboard planning assistant. "
            "Return only valid JSON for the response model."
        )
        user = (
            f"request_id: {request_id}\n"
            f"question: {request.question}\n"
            f"dataset_ids: {', '.join(request.dataset_ids)}\n"
            f"theme: {request.theme}\n"
            "Create a semantic DashboardPlan. Do not emit pixel coordinates, frame, x, y, "
            "width, or height. Organize widgets into named regions. Every widget must use a "
            "single dataset_id. Never perform a cross-dataset join in one widget. Use only "
            "declared fields and safe aggregations; do not emit SQL or executable code.\n"
            f"datasets: {json.dumps(dataset_description, ensure_ascii=False)}\n"
            f"contexts: {serialized_contexts}"
        )
        return system, user

    @staticmethod
    def _repair_prompt(user: str, issues: tuple[PlanValidationIssue, ...]) -> str:
        serialized = [_repair_issue(issue) for issue in issues]
        return (
            f"{user}\nvalidation_issues: {json.dumps(serialized, ensure_ascii=False)}\n"
            "Repair the plan using only the reported issues and return the complete plan."
        )

    async def generate(
        self,
        request: AiScreenRequest,
        *,
        request_id: str,
    ) -> AiScreenPlanResponse:
        datasets = tuple([await self._dataset(item) for item in request.dataset_ids])
        contexts = await self._context_service.build(
            request.dataset_ids,
            max_rows=self._max_context_rows,
            question=request.question,
        )
        system, user = self._prompt(
            request=request,
            datasets=datasets,
            contexts=contexts,
            request_id=request_id,
        )
        definitions = {dataset.id: dataset.definition for dataset in datasets}
        authorized = set(definitions)
        issues: tuple[PlanValidationIssue, ...] = ()
        last_response: AiScreenPlanResponse | None = None

        for _attempt in range(3):
            response = await self._gateway.complete_json(
                system=system,
                user=self._repair_prompt(user, issues) if issues else user,
                response_model=AiScreenPlanResponse,
            )
            last_response = response
            result = self._validator.validate(
                response.plan,
                datasets=definitions,
                authorized_dataset_ids=authorized,
            )
            if result.valid:
                return response
            issues = result.issues

        assert last_response is not None
        invalid_widget_ids = {issue.widget_id for issue in issues if issue.widget_id is not None}
        retained_widgets = tuple(
            widget for widget in last_response.plan.widgets if widget.id not in invalid_widget_ids
        )
        if retained_widgets:
            payload = last_response.plan.model_dump(mode="json")
            payload["widgets"] = [widget.model_dump(mode="json") for widget in retained_widgets]
            partial = DashboardPlan.model_validate(payload)
            result = self._validator.validate(
                partial,
                datasets=definitions,
                authorized_dataset_ids=authorized,
            )
            if result.valid:
                warnings = list(last_response.warnings)
                warnings.extend(
                    f"已跳过组件 {widget_id}: Plan 校验失败"
                    for widget_id in sorted(invalid_widget_ids)
                )
                return last_response.model_copy(
                    update={"plan": partial, "warnings": tuple(dict.fromkeys(warnings))}
                )

        raise AiAnalysisError(
            "AI_SCREEN_INVALID",
            "The generated dashboard plan is invalid.",
            issues=tuple(_repair_issue(issue) for issue in issues),
        )


__all__ = ["ScreenPlanGenerator"]
