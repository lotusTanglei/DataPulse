from typing import Literal, Self

from pydantic import Field, model_validator

from datapulse.contracts.common import (
    ContractModel,
    JsonValue,
    NonBlankStr,
    PositiveFloat,
    PositiveInt,
)


class Canvas(ContractModel):
    width: PositiveInt
    height: PositiveInt


class Geometry(ContractModel):
    x: float
    y: float
    width: PositiveFloat
    height: PositiveFloat
    rotation: float = 0
    z_index: int = 0


class PluginRef(ContractModel):
    id: NonBlankStr
    version: NonBlankStr


class ComponentInstance(ContractModel):
    id: NonBlankStr
    type: NonBlankStr
    plugin: PluginRef
    geometry: Geometry
    data_binding: dict[str, JsonValue] = Field(default_factory=dict)
    properties: dict[str, JsonValue] = Field(default_factory=dict)
    style: dict[str, JsonValue] = Field(default_factory=dict)


class Theme(ContractModel):
    variables: dict[str, JsonValue] = Field(default_factory=dict)


class DashboardParameter(ContractModel):
    id: NonBlankStr
    name: NonBlankStr
    value: JsonValue = None


class Interaction(ContractModel):
    id: NonBlankStr
    source_component_id: NonBlankStr
    event: NonBlankStr
    action: NonBlankStr
    target_component_id: str | None = None
    parameter: str | None = None


class DashboardDocument(ContractModel):
    schema_version: Literal[1] = 1
    canvas: Canvas
    theme: Theme = Field(default_factory=Theme)
    parameters: tuple[DashboardParameter, ...] = Field(default_factory=tuple)
    components: tuple[ComponentInstance, ...] = Field(default_factory=tuple)
    interactions: tuple[Interaction, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_unique_component_ids(self) -> Self:
        component_ids = [component.id for component in self.components]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("component IDs must be unique")
        return self
