from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

import pytest
from pydantic import ValidationError

from datapulse.contracts.dataset import DatasetDefinition, DatasetField, DataType, SqlQuery
from datapulse.dataset.models import DatasetResponse

pytestmark = pytest.mark.anyio


def _contracts() -> Any:
    return importlib.import_module("datapulse.contracts.dataset")


def _service_module() -> Any:
    return importlib.import_module("datapulse.dataset.semantics")


def _dataset(dataset_id: str, source_id: str) -> DatasetResponse:
    return DatasetResponse(
        id=dataset_id,
        name=dataset_id,
        data_source_id=source_id,
        definition=DatasetDefinition(
            id=dataset_id,
            name=dataset_id,
            data_source_id=source_id,
            query=SqlQuery(sql="SELECT id, revenue, cost, year, month FROM facts"),
            fields=(
                DatasetField(name="id", data_type=DataType.STRING),
                DatasetField(name="revenue", data_type=DataType.NUMBER),
                DatasetField(name="cost", data_type=DataType.NUMBER),
                DatasetField(name="year", data_type=DataType.INTEGER),
                DatasetField(name="month", data_type=DataType.INTEGER),
            ),
        ),
        created_at="2026-09-23T00:00:00Z",
        updated_at="2026-09-23T00:00:00Z",
    )


@dataclass
class FakeRepository:
    values: dict[str, DatasetResponse]

    async def get(self, dataset_id: str) -> DatasetResponse:
        return self.values[dataset_id]

    async def update(self, dataset_id: str, definition: DatasetDefinition) -> DatasetResponse:
        current = self.values[dataset_id]
        updated = current.model_copy(update={"definition": definition})
        self.values[dataset_id] = updated
        return updated


def test_semantic_contract_supports_controlled_calculation_metric_and_hierarchy() -> None:
    contracts = _contracts()

    semantics = contracts.DatasetSemantics.model_validate(
        {
            "calculated_fields": [
                {
                    "name": "margin",
                    "label": "利润率",
                    "data_type": "number",
                    "expression": {
                        "left_field": "revenue",
                        "operator": "divide",
                        "right_field": "cost",
                    },
                    "unit": "%",
                }
            ],
            "metrics": [
                {
                    "name": "average_margin",
                    "label": "平均利润率",
                    "source_field": "margin",
                    "aggregation": "avg",
                    "unit": "%",
                    "format": "0.00%",
                }
            ],
            "hierarchies": [
                {
                    "name": "calendar",
                    "label": "日历层级",
                    "kind": "time",
                    "levels": [
                        {"field": "year", "label": "年", "time_grain": "year"},
                        {"field": "month", "label": "月", "time_grain": "month"},
                    ],
                }
            ],
        }
    )

    assert semantics.calculated_fields[0].expression.operator.value == "divide"
    assert semantics.metrics[0].source_field == "margin"
    assert semantics.hierarchies[0].levels[1].time_grain.value == "month"

    with pytest.raises(ValidationError):
        contracts.DatasetCalculatedField.model_validate(
            {
                "name": "unsafe",
                "label": "不安全",
                "data_type": "number",
                "expression": "__import__('os').system('id')",
            }
        )


async def test_semantics_service_persists_calculations_metrics_and_same_source_links() -> None:
    contracts = _contracts()
    semantics_module = _service_module()
    repository = FakeRepository(
        {
            "facts": _dataset("facts", "source-1"),
            "dimension": _dataset("dimension", "source-1"),
        }
    )
    service = semantics_module.DatasetSemanticsService(repository=repository)
    payload = contracts.DatasetSemantics.model_validate(
        {
            "calculated_fields": [
                {
                    "name": "profit",
                    "label": "利润",
                    "data_type": "number",
                    "expression": {
                        "left_field": "revenue",
                        "operator": "subtract",
                        "right_field": "cost",
                    },
                    "unit": "元",
                }
            ],
            "metrics": [
                {
                    "name": "total_profit",
                    "label": "利润合计",
                    "source_field": "profit",
                    "aggregation": "sum",
                    "unit": "元",
                }
            ],
            "relationships": [
                {
                    "name": "fact_dimension",
                    "target_dataset_id": "dimension",
                    "local_field": "id",
                    "target_field": "id",
                    "cardinality": "many_to_one",
                }
            ],
            "hierarchies": [
                {
                    "name": "calendar",
                    "label": "日历层级",
                    "kind": "time",
                    "levels": [
                        {"field": "year", "label": "年", "time_grain": "year"},
                        {"field": "month", "label": "月", "time_grain": "month"},
                    ],
                }
            ],
        }
    )

    saved = await service.update("facts", payload)

    assert saved == payload
    assert await service.get("facts") == payload
    assert repository.values["facts"].definition.semantics == payload


async def test_semantics_service_rejects_cross_source_relationships_and_unknown_fields() -> None:
    contracts = _contracts()
    semantics_module = _service_module()
    repository = FakeRepository(
        {
            "facts": _dataset("facts", "source-1"),
            "external": _dataset("external", "source-2"),
        }
    )
    service = semantics_module.DatasetSemanticsService(repository=repository)

    cross_source = contracts.DatasetSemantics.model_validate(
        {
            "relationships": [
                {
                    "name": "forbidden",
                    "target_dataset_id": "external",
                    "local_field": "id",
                    "target_field": "id",
                    "cardinality": "many_to_one",
                }
            ]
        }
    )
    with pytest.raises(semantics_module.DatasetSemanticsInvalid, match="same datasource"):
        await service.update("facts", cross_source)

    unknown_field = contracts.DatasetSemantics.model_validate(
        {
            "calculated_fields": [
                {
                    "name": "bad",
                    "label": "错误字段",
                    "data_type": "number",
                    "expression": {
                        "left_field": "missing",
                        "operator": "add",
                        "constant": 1,
                    },
                }
            ]
        }
    )
    with pytest.raises(semantics_module.DatasetSemanticsInvalid, match="unknown field"):
        await service.update("facts", unknown_field)
