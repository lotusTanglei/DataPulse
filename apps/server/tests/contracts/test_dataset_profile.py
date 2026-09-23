from datapulse.dataset.profile import (
    DatasetFieldProfile,
    DatasetProfile,
    DatasetProfilePatch,
    FieldRole,
)


def test_dataset_profile_contract_round_trips_stats_and_corrections() -> None:
    profile = DatasetProfile.model_validate(
        {
            "dataset_id": "sales",
            "name": "销售数据",
            "row_count": 3,
            "sampled": False,
            "fields": [
                {
                    "name": "amount",
                    "data_type": "number",
                    "role": "measure",
                    "nullable": False,
                    "null_rate": 0,
                    "unique_count": 3,
                    "cardinality": 3,
                    "uniqueness_ratio": 1,
                    "min": 10,
                    "max": 30,
                    "top_values": [{"value": 10, "count": 1}],
                    "sample_values": [10, 20],
                    "default_aggregation": "sum",
                    "unit": "元",
                    "display_name": "金额",
                }
            ],
        }
    )
    patch = DatasetProfilePatch(
        fields=[
            {
                "name": "amount",
                "role": FieldRole.DIMENSION,
                "default_aggregation": "avg",
                "unit": "元",
                "display_name": "平均金额",
            }
        ]
    )

    assert profile.fields[0].role is FieldRole.MEASURE
    assert isinstance(profile.fields[0], DatasetFieldProfile)
    assert patch.fields[0].role is FieldRole.DIMENSION
    assert profile.fields[0].top_values[0].count == 1
    assert patch.fields[0].display_name == "平均金额"
