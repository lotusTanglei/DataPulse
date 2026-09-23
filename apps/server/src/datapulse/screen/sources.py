from datapulse.contracts.dataset import DatasetDefinition, FileQuery


def dataset_source_key(dataset: DatasetDefinition) -> str:
    if dataset.data_source_id:
        return f"datasource:{dataset.data_source_id}"
    if isinstance(dataset.query, FileQuery):
        return f"file:{dataset.query.asset_id}"
    return f"{dataset.query.kind}:{dataset.id}"


__all__ = ["dataset_source_key"]
