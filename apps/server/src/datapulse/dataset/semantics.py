from __future__ import annotations

from datapulse.contracts.dataset import DatasetSemantics, DataType
from datapulse.dataset.repository import DatasetRepository


class DatasetSemanticsInvalid(ValueError):
    code = "DATASET_SEMANTICS_INVALID"


class DatasetSemanticsService:
    def __init__(self, *, repository: DatasetRepository) -> None:
        self._repository = repository

    async def get(self, dataset_id: str) -> DatasetSemantics:
        dataset = await self._repository.get(dataset_id)
        return dataset.definition.semantics

    async def update(
        self,
        dataset_id: str,
        semantics: DatasetSemantics,
    ) -> DatasetSemantics:
        dataset = await self._repository.get(dataset_id)
        physical_fields = {field.name: field for field in dataset.definition.fields}
        calculated_fields = {field.name: field for field in semantics.calculated_fields}
        collisions = set(physical_fields) & set(calculated_fields)
        if collisions:
            raise DatasetSemanticsInvalid(
                f"Calculated field conflicts with an existing field: {sorted(collisions)[0]}."
            )
        for field in semantics.calculated_fields:
            references = {field.expression.left_field}
            if field.expression.right_field is not None:
                references.add(field.expression.right_field)
            unknown = references - set(physical_fields)
            if unknown:
                raise DatasetSemanticsInvalid(
                    f"Calculated field references unknown field: {sorted(unknown)[0]}."
                )
            if any(
                physical_fields[name].data_type not in {DataType.INTEGER, DataType.NUMBER}
                for name in references
            ):
                raise DatasetSemanticsInvalid("Calculated field operands must be numeric.")
        metric_sources = set(physical_fields) | set(calculated_fields)
        for metric in semantics.metrics:
            if metric.source_field not in metric_sources:
                raise DatasetSemanticsInvalid(
                    f"Metric references unknown field: {metric.source_field}."
                )
            source_type = (
                physical_fields[metric.source_field].data_type
                if metric.source_field in physical_fields
                else calculated_fields[metric.source_field].data_type
            )
            if metric.aggregation != "count" and source_type not in {
                DataType.INTEGER,
                DataType.NUMBER,
            }:
                raise DatasetSemanticsInvalid("Non-count metrics require a numeric field.")
        hierarchy_fields = metric_sources
        for hierarchy in semantics.hierarchies:
            unknown = {level.field for level in hierarchy.levels} - hierarchy_fields
            if unknown:
                raise DatasetSemanticsInvalid(
                    f"Hierarchy references unknown field: {sorted(unknown)[0]}."
                )
        for relationship in semantics.relationships:
            if relationship.local_field not in physical_fields:
                raise DatasetSemanticsInvalid(
                    f"Relationship references unknown field: {relationship.local_field}."
                )
            target = await self._repository.get(relationship.target_dataset_id)
            if (
                dataset.data_source_id is None
                or target.data_source_id is None
                or dataset.data_source_id != target.data_source_id
            ):
                raise DatasetSemanticsInvalid(
                    "Dataset relationships must reference the same datasource."
                )
            target_fields = {field.name for field in target.definition.fields}
            if relationship.target_field not in target_fields:
                raise DatasetSemanticsInvalid(
                    f"Relationship references unknown field: {relationship.target_field}."
                )
        definition = dataset.definition.model_copy(update={"semantics": semantics})
        await self._repository.update(dataset_id, definition)
        return semantics


__all__ = [
    "DatasetSemanticsInvalid",
    "DatasetSemanticsService",
]
