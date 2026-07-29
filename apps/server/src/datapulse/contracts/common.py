from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints

NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
PositiveFloat = Annotated[float, Field(gt=0)]
PositiveInt = Annotated[int, Field(gt=0)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


__all__ = [
    "ContractModel",
    "JsonValue",
    "NonBlankStr",
    "PositiveFloat",
    "PositiveInt",
]
