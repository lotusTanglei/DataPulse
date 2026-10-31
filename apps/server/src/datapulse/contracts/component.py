import re
from typing import Literal

from pydantic import Field, field_validator

from datapulse.contracts.common import ContractModel, JsonValue, NonBlankStr

_BUILTIN_TYPE = re.compile(r"^builtin\.[a-z][a-z0-9_]*$")
_SEMANTIC_VERSION = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


class ComponentContract(ContractModel):
    schema_version: Literal[1] = 1
    type: NonBlankStr
    version: NonBlankStr
    category: NonBlankStr
    props_schema: dict[str, JsonValue]
    data_input_schema: dict[str, JsonValue]
    default_props: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if not _BUILTIN_TYPE.fullmatch(value):
            raise ValueError("component type must use builtin snake-case syntax")
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if not _SEMANTIC_VERSION.fullmatch(value):
            raise ValueError("version must use semantic version syntax")
        return value

    @field_validator("props_schema", "data_input_schema")
    @classmethod
    def validate_object_schema(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        if value.get("type") != "object" or not isinstance(value.get("properties"), dict):
            raise ValueError("component schemas must describe an object with properties")
        return value


__all__ = ["ComponentContract"]
