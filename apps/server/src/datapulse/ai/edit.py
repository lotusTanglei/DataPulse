from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy

from pydantic import ValidationError

from datapulse.ai.models import AiAnalysisError
from datapulse.contracts.ai import (
    AiEditCommand,
    AiSetComponentStateCommand,
    AiUpdateDataBindingCommand,
    AiUpdateFrameCommand,
    AiUpdatePropsCommand,
    AiUpdateStyleCommand,
)
from datapulse.contracts.chart import ChartSpec, ChartType
from datapulse.contracts.dashboard import DashboardDocument
from datapulse.contracts.dataset import FileQuery, RestQuery, SqlQuery
from datapulse.dataset.models import DatasetResponse
from datapulse.filedata.query import FileQueryCompiler
from datapulse.screen.chart_query import ChartQueryCompiler, ChartQueryInvalid

_COMPONENT_VISUALS: dict[str, set[ChartType] | None] = {
    "builtin.text": None,
    "builtin.image": None,
    "builtin.kpi": {ChartType.KPI},
    "builtin.table": {ChartType.TABLE},
    "builtin.progress": {ChartType.PROGRESS, ChartType.GAUGE},
    "builtin.line": {ChartType.LINE, ChartType.AREA},
    "builtin.bar": {ChartType.BAR},
    "builtin.pie": {ChartType.PIE},
    "builtin.geo_map": {ChartType.MAP},
}

_ALLOWED_PROP_KEYS: dict[str, set[str]] = {
    "builtin.text": {"text", "align", "font_size", "font_weight"},
    "builtin.image": {"asset_id", "alt", "fit"},
    "builtin.kpi": {"label", "precision", "empty_text", "prefix", "suffix"},
    "builtin.table": {"max_rows", "empty_text"},
    "builtin.progress": {"label", "precision", "empty_text"},
    "builtin.line": {"empty_text"},
    "builtin.bar": {"orientation", "empty_text"},
    "builtin.pie": {"variant", "empty_text"},
    "builtin.geo_map": {
        "asset_id",
        "region_code_property",
        "region_name_property",
        "empty_text",
    },
}
_ALLOWED_STYLE_KEYS = {
    "background_color",
    "text_color",
    "border_color",
    "border_width",
    "border_radius",
    "opacity",
}
_ALLOWED_FRAME_KEYS = {"x", "y", "width", "height", "z_index"}
_ALLOWED_STATE_KEYS = {"locked", "hidden", "group_id"}
_BANNED_KEYS = {
    "javascript",
    "script",
    "onclick",
    "on_click",
    "onload",
    "path",
    "src",
    "url",
    "sql",
}


def _invalid(message: str = "The AI edit commands are invalid.") -> AiAnalysisError:
    return AiAnalysisError("AI_EDIT_INVALID", message)


def _assert_safe_json(value: object) -> None:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered.startswith(("http://", "https://", "file://")) or "<script" in lowered:
            raise _invalid()
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().lower() in _BANNED_KEYS:
                raise _invalid()
            _assert_safe_json(item)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            _assert_safe_json(item)


def _component_map(document: DashboardDocument) -> dict[str, dict[str, object]]:
    return {
        component.id: component.model_dump(mode="python")
        for component in document.components
    }


def _assert_known_components(
    components: Mapping[str, object], component_ids: Sequence[str]
) -> None:
    if not component_ids or any(component_id not in components for component_id in component_ids):
        raise _invalid("The AI edit references an unknown component.")


def _assert_unlocked(
    components: Mapping[str, dict[str, object]], component_ids: Sequence[str]
) -> None:
    for component_id in component_ids:
        state = components[component_id].get("state")
        if isinstance(state, dict) and state.get("locked") is True:
            raise _invalid("The AI edit targets a locked component.")


def _assert_patch_keys(patch: Mapping[str, object], allowed: set[str]) -> None:
    _assert_safe_json(patch)
    if not patch or not set(patch) <= allowed:
        raise _invalid()


def _apply_command(
    components: dict[str, dict[str, object]],
    command: AiEditCommand,
) -> None:
    if isinstance(command, AiUpdateFrameCommand):
        _assert_known_components(components, command.component_ids)
        _assert_unlocked(components, command.component_ids)
        _assert_patch_keys(command.patch, _ALLOWED_FRAME_KEYS)
        for key, value in command.patch.items():
            if key in {"x", "y", "width", "height", "z_index"} and (
                not isinstance(value, (int, float)) or isinstance(value, bool)
            ):
                raise _invalid()
        for component_id in command.component_ids:
            frame = components[component_id]["frame"]
            assert isinstance(frame, dict)
            frame.update(deepcopy(command.patch))
        return

    if isinstance(command, AiUpdatePropsCommand):
        _assert_known_components(components, (command.component_id,))
        _assert_unlocked(components, (command.component_id,))
        component = components[command.component_id]
        component_type = component.get("type")
        if not isinstance(component_type, str):
            raise _invalid()
        _assert_patch_keys(command.patch, _ALLOWED_PROP_KEYS.get(component_type, set()))
        props = component["props"]
        if not isinstance(props, dict):
            raise _invalid()
        props.update(deepcopy(command.patch))
        return

    if isinstance(command, AiUpdateStyleCommand):
        _assert_known_components(components, (command.component_id,))
        _assert_unlocked(components, (command.component_id,))
        _assert_patch_keys(command.patch, _ALLOWED_STYLE_KEYS)
        style = components[command.component_id]["style"]
        if not isinstance(style, dict):
            raise _invalid()
        style.update(deepcopy(command.patch))
        return

    if isinstance(command, AiUpdateDataBindingCommand):
        _assert_known_components(components, (command.component_id,))
        _assert_unlocked(components, (command.component_id,))
        _assert_safe_json(command.data_binding)
        if set(command.data_binding) - {"chart_spec"}:
            raise _invalid()
        components[command.component_id]["data_binding"] = deepcopy(command.data_binding)
        return

    if isinstance(command, AiSetComponentStateCommand):
        _assert_known_components(components, command.component_ids)
        _assert_unlocked(components, command.component_ids)
        _assert_patch_keys(command.patch, _ALLOWED_STATE_KEYS)
        for component_id in command.component_ids:
            state = components[component_id]["state"]
            if not isinstance(state, dict):
                raise _invalid()
            state.update(deepcopy(command.patch))
        return

    raise _invalid()


def apply_ai_edit_commands(
    document: DashboardDocument,
    commands: Sequence[AiEditCommand],
) -> DashboardDocument:
    if not commands or len(commands) > 8:
        raise _invalid()
    components = _component_map(document)
    for command in commands:
        _apply_command(components, command)
    payload = document.model_dump(mode="python")
    payload["components"] = list(components.values())
    try:
        updated = DashboardDocument.model_validate(payload)
    except (ValidationError, TypeError, ValueError) as error:
        raise _invalid() from error
    _validate_bounds(updated)
    return updated


def _validate_bounds(document: DashboardDocument) -> None:
    for component in document.components:
        frame = component.frame
        if (
            frame.x < 0
            or frame.y < 0
            or frame.x + frame.width > document.canvas.width
            or frame.y + frame.height > document.canvas.height
        ):
            raise _invalid("The AI edit places a component outside the canvas.")


def validate_edit_document(
    document: DashboardDocument,
    datasets_by_id: Mapping[str, DatasetResponse],
) -> DashboardDocument:
    parameter_defaults = {
        parameter.name: parameter.default for parameter in document.parameters
    }
    for component in document.components:
        binding = component.data_binding or {}
        if not binding:
            continue
        if set(binding) != {"chart_spec"}:
            raise _invalid()
        try:
            spec = ChartSpec.model_validate(binding["chart_spec"])
        except (ValidationError, TypeError, ValueError) as error:
            raise _invalid() from error
        allowed_visuals = _COMPONENT_VISUALS.get(component.type)
        if allowed_visuals is None or spec.visual.type not in allowed_visuals:
            raise _invalid()
        dataset = datasets_by_id.get(spec.dataset_id)
        if dataset is None:
            raise AiAnalysisError("AI_DATASET_INVALID", "The dataset is invalid.")
        try:
            if isinstance(dataset.definition.query, SqlQuery):
                ChartQueryCompiler().compile(spec, dataset.definition, parameter_defaults)
            elif isinstance(dataset.definition.query, FileQuery):
                FileQueryCompiler().compile(spec, dataset.definition, None, parameter_defaults)
            elif isinstance(dataset.definition.query, RestQuery):
                requested_fields = {
                    *spec.dimensions,
                    *(measure.field for measure in spec.measures),
                    *(filter_.field for filter_ in spec.filters),
                    *(sort.field for sort in spec.sort),
                }
                known_fields = {field.name for field in dataset.definition.fields}
                if not requested_fields <= known_fields:
                    raise _invalid()
            else:
                raise _invalid()
        except ChartQueryInvalid as error:
            raise _invalid() from error
    _validate_bounds(document)
    return document


__all__ = ["apply_ai_edit_commands", "validate_edit_document"]
