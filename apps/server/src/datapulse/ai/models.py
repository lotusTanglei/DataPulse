from typing import Literal

from datapulse.contracts.common import ContractModel, JsonValue


class AiHealth(ContractModel):
    status: Literal["configured", "unconfigured", "unavailable"]
    model: str | None = None


class AiGatewayError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class AiAnalysisError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class DatasetContextField(ContractModel):
    name: str
    data_type: str


class DatasetContext(ContractModel):
    dataset_id: str
    name: str
    fields: tuple[DatasetContextField, ...]
    sample_rows: tuple[dict[str, JsonValue], ...]
    summary: str


__all__ = [
    "AiAnalysisError",
    "AiGatewayError",
    "AiHealth",
    "DatasetContext",
    "DatasetContextField",
]
