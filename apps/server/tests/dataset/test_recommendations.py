from datapulse.contracts.dataset import DataType
from datapulse.dataset.profile import DatasetFieldProfile, DatasetProfile, FieldRole
from datapulse.dataset.recommendations import recommend_dataset


def profile(*fields: DatasetFieldProfile) -> DatasetProfile:
    return DatasetProfile(
        dataset_id="scenario",
        name="场景数据",
        row_count=100,
        sampled=False,
        fields=fields,
    )


def field(name: str, data_type: DataType, role: FieldRole) -> DatasetFieldProfile:
    return DatasetFieldProfile(
        name=name,
        data_type=data_type,
        role=role,
        nullable=False,
        unique_count=10,
        cardinality=10,
        uniqueness_ratio=0.1,
    )


def test_rule_recommendations_cover_roles_aggregations_and_chart_shapes() -> None:
    result = recommend_dataset(
        profile(
            field("订单号", DataType.STRING, FieldRole.IDENTIFIER),
            field("日期", DataType.DATE, FieldRole.TEMPORAL),
            field("区域", DataType.STRING, FieldRole.GEOGRAPHY),
            field("渠道", DataType.STRING, FieldRole.DIMENSION),
            field("销售额", DataType.NUMBER, FieldRole.MEASURE),
        )
    )

    by_field = {item.field: item for item in result.fields}
    assert by_field["订单号"].role is FieldRole.IDENTIFIER
    assert by_field["订单号"].aggregation == "count"
    assert by_field["销售额"].aggregation == "sum"
    assert [item.chart_type.value for item in result.charts] == [
        "map",
        "line",
        "bar",
        "kpi",
    ]
    assert all(item.dataset_id == "scenario" for item in result.charts)


def test_rule_chart_recommendation_accuracy_sample_is_at_least_ninety_percent() -> None:
    samples = (
        (("日期", DataType.DATE, FieldRole.TEMPORAL), "line"),
        (("月份", DataType.DATE, FieldRole.TEMPORAL), "line"),
        (("区域", DataType.STRING, FieldRole.GEOGRAPHY), "map"),
        (("省份", DataType.STRING, FieldRole.GEOGRAPHY), "map"),
        (("渠道", DataType.STRING, FieldRole.DIMENSION), "bar"),
        (("产品", DataType.STRING, FieldRole.DIMENSION), "bar"),
        (("状态", DataType.STRING, FieldRole.DIMENSION), "bar"),
        (("销售额", DataType.NUMBER, FieldRole.MEASURE), "kpi"),
        (("订单数", DataType.INTEGER, FieldRole.MEASURE), "kpi"),
        (("故障率", DataType.NUMBER, FieldRole.MEASURE), "kpi"),
    )
    matches = 0
    for (name, data_type, role), expected in samples:
        fields = [field(name, data_type, role)]
        if role is not FieldRole.MEASURE:
            fields.append(field("指标值", DataType.NUMBER, FieldRole.MEASURE))
        recommendation = recommend_dataset(profile(*fields))
        matches += recommendation.charts[0].chart_type.value == expected

    assert matches / len(samples) >= 0.9
