from pydantic import Field

from datapulse.contracts.chart import Aggregation, ChartType
from datapulse.contracts.common import ContractModel, NonBlankStr
from datapulse.dataset.profile import DatasetProfile, FieldRole


class FieldRecommendation(ContractModel):
    field: NonBlankStr
    role: FieldRole
    aggregation: Aggregation


class ChartRecommendation(ContractModel):
    dataset_id: NonBlankStr
    chart_type: ChartType
    dimensions: tuple[NonBlankStr, ...] = Field(default_factory=tuple)
    measures: tuple[NonBlankStr, ...] = Field(default_factory=tuple)
    reason: NonBlankStr


class DatasetRecommendations(ContractModel):
    dataset_id: NonBlankStr
    fields: tuple[FieldRecommendation, ...] = Field(default_factory=tuple)
    charts: tuple[ChartRecommendation, ...] = Field(default_factory=tuple)


def _aggregation(role: FieldRole, configured: str | None) -> Aggregation:
    if configured is not None:
        try:
            return Aggregation(configured)
        except ValueError:
            pass
    return Aggregation.SUM if role is FieldRole.MEASURE else Aggregation.COUNT


def recommend_dataset(profile: DatasetProfile) -> DatasetRecommendations:
    fields = tuple(
        FieldRecommendation(
            field=item.name,
            role=item.role,
            aggregation=_aggregation(item.role, item.default_aggregation),
        )
        for item in profile.fields
    )
    measures = [item.name for item in profile.fields if item.role is FieldRole.MEASURE]
    temporal = [item.name for item in profile.fields if item.role is FieldRole.TEMPORAL]
    geography = [item.name for item in profile.fields if item.role is FieldRole.GEOGRAPHY]
    dimensions = [item.name for item in profile.fields if item.role is FieldRole.DIMENSION]
    charts: list[ChartRecommendation] = []
    measure = measures[0] if measures else None
    if measure is not None and geography:
        charts.append(
            ChartRecommendation(
                dataset_id=profile.dataset_id,
                chart_type=ChartType.MAP,
                dimensions=(geography[0],),
                measures=(measure,),
                reason="地理字段与指标适合地图对比",
            )
        )
    if measure is not None and temporal:
        charts.append(
            ChartRecommendation(
                dataset_id=profile.dataset_id,
                chart_type=ChartType.LINE,
                dimensions=(temporal[0],),
                measures=(measure,),
                reason="时间字段与指标适合趋势分析",
            )
        )
    if measure is not None and dimensions:
        charts.append(
            ChartRecommendation(
                dataset_id=profile.dataset_id,
                chart_type=ChartType.BAR,
                dimensions=(dimensions[0],),
                measures=(measure,),
                reason="分类字段与指标适合分类比较",
            )
        )
    if measure is not None:
        charts.append(
            ChartRecommendation(
                dataset_id=profile.dataset_id,
                chart_type=ChartType.KPI,
                measures=(measure,),
                reason="指标字段适合汇总展示",
            )
        )
    if not charts and profile.fields:
        charts.append(
            ChartRecommendation(
                dataset_id=profile.dataset_id,
                chart_type=ChartType.TABLE,
                dimensions=tuple(item.name for item in profile.fields[:3]),
                reason="缺少数值指标时使用明细表",
            )
        )
    return DatasetRecommendations(
        dataset_id=profile.dataset_id,
        fields=fields,
        charts=tuple(charts),
    )


__all__ = [
    "ChartRecommendation",
    "DatasetRecommendations",
    "FieldRecommendation",
    "recommend_dataset",
]
