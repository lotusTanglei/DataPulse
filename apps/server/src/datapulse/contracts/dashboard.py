from typing import Literal, Self

from pydantic import Field, model_validator

from datapulse.contracts.common import (
    ContractModel,
    JsonValue,
    NonBlankStr,
    PositiveFloat,
    PositiveInt,
)
from datapulse.contracts.dataset import DataType
from datapulse.contracts.digital_human import DigitalHumanBinding, DigitalHumanSpec
from datapulse.contracts.plugin import PluginManifest


class Canvas(ContractModel):
    width: PositiveInt
    height: PositiveInt
    background: dict[str, JsonValue] = Field(default_factory=dict)


class Frame(ContractModel):
    x: float
    y: float
    width: PositiveFloat
    height: PositiveFloat
    z_index: int = 0


class ComponentState(ContractModel):
    locked: bool = False
    hidden: bool = False
    group_id: NonBlankStr | None = None


class ComponentInteraction(ContractModel):
    event: Literal["click"]
    action: Literal["set_parameter"]
    parameter: NonBlankStr
    field: NonBlankStr


class ComponentInstance(ContractModel):
    id: NonBlankStr
    type: NonBlankStr
    frame: Frame
    state: ComponentState = Field(default_factory=ComponentState)
    props: dict[str, JsonValue] = Field(default_factory=dict)
    style: dict[str, JsonValue] = Field(default_factory=dict)
    data_binding: dict[str, JsonValue] = Field(default_factory=dict)
    interactions: tuple[ComponentInteraction, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_digital_human(self) -> Self:
        if self.type == "builtin.digital_human":
            DigitalHumanSpec.model_validate(self.props)
            if self.data_binding.get("source") == "components":
                DigitalHumanBinding.model_validate(self.data_binding)
        elif self.data_binding.get("source") == "components":
            raise ValueError("Component references are only supported by digital humans.")
        return self


class Theme(ContractModel):
    id: NonBlankStr = "datapulse-dark"
    tokens: dict[str, JsonValue] = Field(default_factory=dict)


class ScreenRefreshPolicy(ContractModel):
    mode: Literal["disabled", "interval"] = "disabled"
    interval_seconds: Literal[10, 30, 60, 300] | None = None

    @model_validator(mode="after")
    def validate_interval(self) -> Self:
        if self.mode == "interval" and self.interval_seconds is None:
            raise ValueError("interval_seconds is required for interval refresh")
        if self.mode == "disabled" and self.interval_seconds is not None:
            raise ValueError("interval_seconds must be absent when refresh is disabled")
        return self


class DashboardParameter(ContractModel):
    id: NonBlankStr
    name: NonBlankStr
    data_type: DataType
    default: JsonValue = None
    mutable: bool = False
    allowed_values: tuple[JsonValue, ...] = Field(default_factory=tuple)


class PluginDependency(ContractModel):
    id: NonBlankStr
    version: NonBlankStr

    @model_validator(mode="after")
    def validate_exact_version(self) -> Self:
        PluginManifest.validate_id(self.id)
        PluginManifest.validate_version(self.version)
        return self


class DashboardDocument(ContractModel):
    schema_version: Literal[1] = 1
    canvas: Canvas
    theme: Theme = Field(default_factory=Theme)
    refresh: ScreenRefreshPolicy = Field(default_factory=ScreenRefreshPolicy)
    parameters: tuple[DashboardParameter, ...] = Field(default_factory=tuple)
    components: tuple[ComponentInstance, ...] = Field(default_factory=tuple)
    plugin_dependencies: tuple[PluginDependency, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_document_references(self) -> Self:
        plugin_ids = [dependency.id for dependency in self.plugin_dependencies]
        if len(plugin_ids) != len(set(plugin_ids)):
            raise ValueError("a document must reference one exact version per plugin")
        component_ids = [component.id for component in self.components]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("component IDs must be unique")

        parameter_ids = [parameter.id for parameter in self.parameters]
        if len(parameter_ids) != len(set(parameter_ids)):
            raise ValueError("parameter IDs must be unique")

        parameter_names = [parameter.name for parameter in self.parameters]
        if len(parameter_names) != len(set(parameter_names)):
            raise ValueError("parameter names must be unique")

        known_parameters = set(parameter_names)
        for component in self.components:
            for interaction in component.interactions:
                if interaction.parameter not in known_parameters:
                    raise ValueError(
                        f"component interaction references unknown parameter "
                        f"{interaction.parameter!r}"
                    )
        return self
