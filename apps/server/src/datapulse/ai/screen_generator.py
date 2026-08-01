from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from pydantic import Field, ValidationError

from datapulse.ai.context import DatasetContextService
from datapulse.ai.gateway import AiGateway
from datapulse.ai.models import AiAnalysisError
from datapulse.contracts.ai import AiScreenRequest, AiScreenResponse
from datapulse.contracts.chart import ChartSpec, ChartType
from datapulse.contracts.common import ContractModel, JsonValue, NonBlankStr
from datapulse.contracts.dashboard import DashboardDocument
from datapulse.contracts.dataset import FileQuery, SqlQuery
from datapulse.dataset.models import DatasetResponse
from datapulse.dataset.repository import (
    DatasetDefinitionInvalid,
    DatasetNotFound,
    DatasetRepository,
)
from datapulse.filedata.query import FileQueryCompiler
from datapulse.screen.chart_query import ChartQueryCompiler, ChartQueryInvalid

_DEFAULT_THEME_IDS = {
    "dark": "datapulse-dark",
    "light": "datapulse-light",
}

_MAX_COMPONENTS = 12

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

_DEFAULT_PROPS: dict[str, dict[str, JsonValue]] = {
    "builtin.text": {"text": "文本", "align": "left", "font_size": 24},
    "builtin.image": {"asset_id": "", "alt": "", "fit": "cover"},
    "builtin.kpi": {"label": "指标", "precision": 0, "empty_text": "暂无数据"},
    "builtin.table": {"max_rows": 100, "empty_text": "暂无数据"},
    "builtin.progress": {"label": "进度", "precision": 0, "empty_text": "暂无数据"},
    "builtin.line": {"empty_text": "暂无数据"},
    "builtin.bar": {"orientation": "vertical", "empty_text": "暂无数据"},
    "builtin.pie": {"variant": "pie", "empty_text": "暂无数据"},
    "builtin.geo_map": {
        "asset_id": "",
        "region_code_property": "code",
        "region_name_property": "name",
        "empty_text": "暂无数据",
    },
}

_ALLOWED_PROP_KEYS = {
    component_type: set(defaults) for component_type, defaults in _DEFAULT_PROPS.items()
}

_BANNED_DOCUMENT_KEYS = {
    "auto_publish",
    "publish",
    "published",
    "published_at",
    "published_document",
}
_BANNED_PROP_KEYS = {
    "script",
    "javascript",
    "on_click",
    "onclick",
    "onload",
    "src",
    "url",
    "path",
    "image_url",
    "image_path",
    "sql",
}
_ALLOWED_DOCUMENT_KEYS = {
    "schema_version",
    "canvas",
    "theme",
    "refresh",
    "parameters",
    "components",
}
_ALLOWED_COMPONENT_KEYS = {
    "id",
    "type",
    "frame",
    "state",
    "props",
    "style",
    "data_binding",
    "interactions",
}
_ALLOWED_CHART_SPEC_KEYS = {
    "schema_version",
    "dataset_id",
    "dimensions",
    "measures",
    "filters",
    "sort",
    "limit",
    "visual",
}


class _AiScreenDraftResponse(ContractModel):
    document: dict[str, JsonValue]
    explanation: NonBlankStr
    warnings: tuple[str, ...] = Field(default_factory=tuple)


def _screen_error(code: str = "AI_SCREEN_INVALID") -> AiAnalysisError:
    return AiAnalysisError(code, "The screen draft is invalid.")


def _mapping(value: object, *, code: str = "AI_SCREEN_INVALID") -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise _screen_error(code)
    return dict(value)


def _sequence(value: object, *, code: str = "AI_SCREEN_INVALID") -> list[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise _screen_error(code)
    return list(value)


def _contains_unsafe_text(value: str) -> bool:
    lowered = value.strip().lower()
    return (
        "<script" in lowered
        or "javascript:" in lowered
        or lowered.startswith("http://")
        or lowered.startswith("https://")
        or lowered.startswith("file://")
    )


def _assert_safe_json(value: object) -> None:
    if isinstance(value, str) and _contains_unsafe_text(value):
        raise _screen_error()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().lower() in _BANNED_PROP_KEYS:
                raise _screen_error()
            _assert_safe_json(item)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            _assert_safe_json(item)


def _sanitize_canvas(
    payload: object,
    *,
    canvas_width: int,
    canvas_height: int,
    requested_theme: str,
) -> dict[str, JsonValue]:
    background_color = "#0b1020" if requested_theme == "dark" else "#f8fafc"
    if payload is None:
        return {
            "width": canvas_width,
            "height": canvas_height,
            "background": {"color": background_color},
        }
    value = _mapping(payload)
    background = value.get("background")
    safe_background = background if isinstance(background, Mapping) else {"color": background_color}
    _assert_safe_json(safe_background)
    return {
        "width": canvas_width,
        "height": canvas_height,
        "background": dict(safe_background),
    }


def _sanitize_theme(requested_theme: str) -> dict[str, JsonValue]:
    return {
        "id": _DEFAULT_THEME_IDS[requested_theme],
        "tokens": {},
    }


def _sanitize_parameters(payload: object) -> list[dict[str, object]]:
    if payload is None:
        return []
    parameters: list[dict[str, object]] = []
    for item in _sequence(payload):
        value = _mapping(item)
        parameters.append(
            {
                key: value[key]
                for key in ("id", "name", "data_type", "default", "mutable", "allowed_values")
                if key in value
            }
        )
    return parameters


def _sanitize_props(component_type: str, payload: object) -> dict[str, JsonValue]:
    raw = {} if payload is None else _mapping(payload)
    for key in raw:
        if key.strip().lower() in _BANNED_PROP_KEYS:
            raise _screen_error()
    allowed_keys = _ALLOWED_PROP_KEYS[component_type]
    props = dict(_DEFAULT_PROPS[component_type])
    for key, value in raw.items():
        if key in allowed_keys:
            if key == "asset_id" and isinstance(value, str):
                lowered = value.strip().lower()
                if (
                    lowered.startswith("http://")
                    or lowered.startswith("https://")
                    or lowered.startswith("file://")
                    or lowered.startswith("/")
                ):
                    raise _screen_error()
            _assert_safe_json(value)
            props[key] = value
    return props


def _sanitize_frame(payload: object) -> dict[str, object]:
    value = _mapping(payload)
    frame = {key: value[key] for key in ("x", "y", "width", "height", "z_index") if key in value}
    return frame


def _validate_chart_spec(
    *,
    component_type: str,
    payload: object,
    datasets_by_id: Mapping[str, DatasetResponse],
    parameter_defaults: Mapping[str, JsonValue],
) -> dict[str, JsonValue]:
    allowed_visuals = _COMPONENT_VISUALS[component_type]
    if allowed_visuals is None:
        raise _screen_error()
    raw = _mapping(payload)
    _assert_safe_json(raw)
    spec_payload = {key: raw[key] for key in _ALLOWED_CHART_SPEC_KEYS if key in raw}
    try:
        spec = ChartSpec.model_validate(spec_payload)
    except (ValidationError, TypeError, ValueError) as error:
        raise _screen_error() from error

    if spec.visual.type not in allowed_visuals:
        raise _screen_error()
    dataset = datasets_by_id.get(spec.dataset_id)
    if dataset is None:
        raise _screen_error("AI_DATASET_INVALID")

    try:
        if isinstance(dataset.definition.query, SqlQuery):
            ChartQueryCompiler().compile(spec, dataset.definition, parameter_defaults)
        elif isinstance(dataset.definition.query, FileQuery):
            FileQueryCompiler().compile(spec, dataset.definition, None, parameter_defaults)
        else:
            raise _screen_error()
    except ChartQueryInvalid as error:
        if error.code == "CHART_DATASET_MISMATCH":
            raise _screen_error("AI_DATASET_INVALID") from error
        raise _screen_error() from error

    return spec.model_dump(mode="json")


def _sanitize_data_binding(
    *,
    component_type: str,
    payload: object,
    datasets_by_id: Mapping[str, DatasetResponse],
    parameter_defaults: Mapping[str, JsonValue],
) -> dict[str, JsonValue]:
    if _COMPONENT_VISUALS[component_type] is None:
        if payload not in (None, {}, ()):
            value = _mapping(payload)
            if value:
                raise _screen_error()
        return {}
    value = _mapping(payload)
    chart_spec = value.get("chart_spec")
    if chart_spec is None:
        raise _screen_error()
    return {
        "chart_spec": _validate_chart_spec(
            component_type=component_type,
            payload=chart_spec,
            datasets_by_id=datasets_by_id,
            parameter_defaults=parameter_defaults,
        )
    }


def _sanitize_component(
    payload: object,
    *,
    index: int,
    datasets_by_id: Mapping[str, DatasetResponse],
    parameter_defaults: Mapping[str, JsonValue],
) -> dict[str, object]:
    value = _mapping(payload)
    component_type = value.get("type")
    if not isinstance(component_type, str) or component_type not in _COMPONENT_VISUALS:
        raise _screen_error()
    for key in value:
        if key not in _ALLOWED_COMPONENT_KEYS and key in _BANNED_DOCUMENT_KEYS:
            raise _screen_error()
    component = {
        "id": value.get("id") or f"ai-component-{index + 1}",
        "type": component_type,
        "frame": _sanitize_frame(value.get("frame")),
        "state": value.get("state") if isinstance(value.get("state"), Mapping) else {},
        "props": _sanitize_props(component_type, value.get("props")),
        "style": value.get("style") if isinstance(value.get("style"), Mapping) else {},
        "data_binding": _sanitize_data_binding(
            component_type=component_type,
            payload=value.get("data_binding"),
            datasets_by_id=datasets_by_id,
            parameter_defaults=parameter_defaults,
        ),
        "interactions": value.get("interactions")
        if isinstance(value.get("interactions"), Sequence)
        and not isinstance(value.get("interactions"), (str, bytes, bytearray))
        else [],
    }
    _assert_safe_json(component["state"])
    _assert_safe_json(component["style"])
    _assert_safe_json(component["interactions"])
    return component


def _validate_component_bounds(document: DashboardDocument) -> None:
    canvas = document.canvas
    for component in document.components:
        frame = component.frame
        if (
            frame.x < 0
            or frame.y < 0
            or frame.x + frame.width > canvas.width
            or frame.y + frame.height > canvas.height
        ):
            raise _screen_error()


def validate_ai_document(
    document: object,
    *,
    allowed_dataset_ids: Mapping[str, DatasetResponse],
    canvas_width: int,
    canvas_height: int,
    requested_theme: str,
) -> DashboardDocument:
    value = _mapping(document)
    if any(key in _BANNED_DOCUMENT_KEYS for key in value):
        raise _screen_error()
    if value.get("components") is None:
        raise _screen_error()
    raw_parameters = _sanitize_parameters(value.get("parameters"))
    parameter_defaults = {
        parameter["name"]: parameter.get("default")
        for parameter in raw_parameters
        if isinstance(parameter.get("name"), str)
    }
    components = [
        _sanitize_component(
            item,
            index=index,
            datasets_by_id=allowed_dataset_ids,
            parameter_defaults=parameter_defaults,
        )
        for index, item in enumerate(_sequence(value.get("components")))
    ]
    if len(components) > _MAX_COMPONENTS:
        raise _screen_error()

    normalized = {key: value[key] for key in _ALLOWED_DOCUMENT_KEYS if key in value}
    normalized["canvas"] = _sanitize_canvas(
        normalized.get("canvas"),
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        requested_theme=requested_theme,
    )
    normalized["theme"] = _sanitize_theme(requested_theme)
    normalized["refresh"] = (
        normalized.get("refresh")
        if isinstance(normalized.get("refresh"), Mapping)
        else {"mode": "disabled"}
    )
    normalized["parameters"] = raw_parameters
    normalized["components"] = components

    try:
        validated = DashboardDocument.model_validate(normalized)
    except (ValidationError, TypeError, ValueError) as error:
        raise _screen_error() from error
    _validate_component_bounds(validated)
    return validated


class ScreenDraftGenerator:
    def __init__(
        self,
        *,
        gateway: AiGateway,
        context_service: DatasetContextService | None = None,
        dataset_repository: DatasetRepository | None = None,
        max_context_rows: int = 100,
    ) -> None:
        self._gateway = gateway
        self._context_service = context_service
        self._dataset_repository = dataset_repository
        self._max_context_rows = max_context_rows

    async def _dataset(self, dataset_id: str) -> DatasetResponse:
        if self._dataset_repository is None:
            raise RuntimeError("dataset repository is not configured")
        try:
            return await self._dataset_repository.get(dataset_id)
        except (DatasetNotFound, DatasetDefinitionInvalid) as error:
            raise AiAnalysisError("AI_DATASET_INVALID", "The dataset is invalid.") from error

    def _prompt(
        self,
        *,
        request: AiScreenRequest,
        datasets: tuple[DatasetResponse, ...],
        contexts: tuple[object, ...],
        request_id: str,
    ) -> tuple[str, str]:
        datasets_description = [
            {
                "dataset_id": dataset.id,
                "name": dataset.name,
                "fields": [
                    {"name": field.name, "data_type": field.data_type.value}
                    for field in dataset.definition.fields
                ],
                "parameters": [
                    {"name": parameter.name, "data_type": parameter.data_type.value}
                    for parameter in dataset.definition.parameters
                ],
            }
            for dataset in datasets
        ]
        system = (
            "You are a DataPulse screen design assistant. "
            "Return only valid JSON for the response model."
        )
        serialized_contexts = json.dumps(
            [item.model_dump(mode="json") for item in contexts],
            ensure_ascii=False,
        )
        user = (
            f"request_id: {request_id}\n"
            f"question: {request.question}\n"
            f"dataset_ids: {', '.join(request.dataset_ids)}\n"
            f"canvas: {request.canvas_width}x{request.canvas_height}\n"
            f"theme: {request.theme}\n"
            f"allowed_component_types: {', '.join(_COMPONENT_VISUALS)}\n"
            "rules: max 12 components; use only builtin components; do not emit SQL; "
            "do not emit JavaScript; do not emit image paths or external URLs; "
            "for data components include chart_spec with dataset_id, fields, filters, and visual.\n"
            f"datasets: {json.dumps(datasets_description, ensure_ascii=False)}\n"
            f"contexts: {serialized_contexts}"
        )
        return system, user

    async def generate(
        self,
        request: AiScreenRequest,
        *,
        request_id: str,
    ) -> AiScreenResponse:
        if self._context_service is None:
            raise RuntimeError("context service is not configured")
        datasets = tuple([await self._dataset(dataset_id) for dataset_id in request.dataset_ids])
        contexts = await self._context_service.build(
            request.dataset_ids,
            max_rows=self._max_context_rows,
        )
        system, user = self._prompt(
            request=request,
            datasets=datasets,
            contexts=contexts,
            request_id=request_id,
        )
        response = await self._gateway.complete_json(
            system=system,
            user=user,
            response_model=_AiScreenDraftResponse,
        )
        document = validate_ai_document(
            response.document,
            allowed_dataset_ids={dataset.id: dataset for dataset in datasets},
            canvas_width=request.canvas_width,
            canvas_height=request.canvas_height,
            requested_theme=request.theme,
        )
        return AiScreenResponse(
            document=document,
            explanation=response.explanation,
            warnings=response.warnings,
        )


__all__ = ["ScreenDraftGenerator", "validate_ai_document"]
