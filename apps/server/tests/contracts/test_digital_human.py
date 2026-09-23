import pytest
from pydantic import ValidationError

from datapulse.contracts.dashboard import ComponentInstance
from datapulse.contracts.digital_human import (
    DigitalHumanAction,
    DigitalHumanBinding,
    DigitalHumanSpec,
    DigitalHumanTrigger,
    SpeechRecording,
    SpeechScriptSegment,
)
from datapulse.contracts.embed import DigitalHumanCommand, DigitalHumanEvent
from datapulse.contracts.speech_template import parse_speech_template


def test_action_contract_is_bounded_and_unique_in_spec() -> None:
    action = DigitalHumanAction(
        id="wave", kind="wave", asset_id="asset-1", asset_kind="video", priority=10
    )
    assert action.duration_ms == 1200
    assert action.priority == 10
    with pytest.raises(ValidationError):
        DigitalHumanAction(id="wave", asset_id="asset-1", priority=101)
    with pytest.raises(ValidationError):
        DigitalHumanSpec(actions=(action, action))


def test_subtitle_colors_and_size_are_safe_for_runtime_styles() -> None:
    spec = DigitalHumanSpec(subtitle_color="#FFFFFF", subtitle_background="#000000CC")
    assert spec.subtitle_color == "#FFFFFF"
    with pytest.raises(ValidationError, match="contrast"):
        DigitalHumanSpec(subtitle_color="#FFFFFF", subtitle_background="#EEEEEE")
    with pytest.raises(ValidationError):
        DigitalHumanSpec(subtitle_color="red")
    with pytest.raises(ValidationError):
        DigitalHumanSpec(subtitle_font_size=11)


def test_template_grammar_supports_unicode_fields_and_bounded_formatting() -> None:
    tokens = parse_speech_template(
        '本月 {{sales.value | number:"0.0a"}}，{{销售额 | currency:"CNY"}}'
    )
    assert [(token.name, token.format, token.option) for token in tokens] == [
        ("sales.value", "number", "0.0a"),
        ("销售额", "currency", "CNY"),
    ]


def test_template_grammar_supports_enum_rank_trend_and_chinese_number_formats() -> None:
    tokens = parse_speech_template(
        "{{state | enum}} {{position | rank}} {{change | trend}} {{total | number_zh}}"
    )
    assert [token.format for token in tokens] == ["enum", "rank", "trend", "number_zh"]


def test_structured_speech_segments_bound_paragraphs_pauses_and_emphasis() -> None:
    spec = DigitalHumanSpec(
        speech_segments=(
            SpeechScriptSegment(kind="paragraph", text="开场"),
            SpeechScriptSegment(kind="pause", duration_ms=800),
            SpeechScriptSegment(kind="emphasis", text="重点"),
        )
    )
    assert [segment.kind for segment in spec.speech_segments] == ["paragraph", "pause", "emphasis"]
    with pytest.raises(ValidationError):
        SpeechScriptSegment(kind="paragraph")
    with pytest.raises(ValidationError):
        SpeechScriptSegment(kind="pause", text="不能有文本")
    with pytest.raises(ValidationError):
        DigitalHumanSpec(speech_segments=(SpeechScriptSegment(kind="pause"),))
    with pytest.raises(ValidationError):
        DigitalHumanSpec(speech_segments=tuple(SpeechScriptSegment(text="x") for _ in range(51)))


@pytest.mark.parametrize("template", ['{{state | enum:"x"}}', '{{total | number_zh:"x"}}'])
def test_non_numeric_speech_formats_reject_options(template: str) -> None:
    with pytest.raises(ValueError):
        parse_speech_template(template)


@pytest.mark.parametrize(
    "text",
    [
        "{{unclosed",
        "unexpected }}",
        "{{value | eval}}",
        "{{value + 1}}",
        "{{constructor}}",
        '{{value | number:"0.000000000"}}',
        '{{value | currency:"not-a-currency"}}',
        '{{value | date:"bad"}}',
        "x" * 4001,
        "{{value}}" * 51,
        "",
    ],
)
def test_invalid_templates_are_rejected(text: str) -> None:
    with pytest.raises((ValueError, ValidationError)):
        DigitalHumanSpec(speech_template=text)


@pytest.mark.parametrize(
    "patch",
    [
        {"rate": 5},
        {"volume": float("nan")},
        {"max_duration_seconds": 301},
        {"avatar_asset_id": "https://external.example/avatar.png"},
        {"audio_asset_id": "../../audio"},
        {"quiet_start": "22:00"},
        {"timezone": "not-a-zone"},
        {"api_key": "must-not-be-in-document"},
    ],
)
def test_invalid_configuration_cannot_enter_screen_document(patch: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ComponentInstance(
            id="speaker",
            type="builtin.digital_human",
            frame={"x": 0, "y": 0, "width": 320, "height": 420},
            props=patch,
        )


@pytest.mark.parametrize("mode", ["mute", "delay", "subtitle"])
def test_quiet_hours_mode_is_explicit_and_bounded(mode: str) -> None:
    spec = DigitalHumanSpec(quiet_start="22:00", quiet_end="07:00", quiet_mode=mode)
    assert spec.quiet_mode == mode


def test_quiet_hours_mode_rejects_unknown_values() -> None:
    with pytest.raises(ValidationError):
        DigitalHumanSpec(quiet_start="22:00", quiet_end="07:00", quiet_mode="speak")


@pytest.mark.parametrize(
    "field",
    [
        "password",
        "access_token",
        "phone",
        "phoneNumber",
        "telephone",
        "emailAddress",
        "apiKey",
        "邮箱",
    ],
)
def test_sensitive_fields_are_not_valid_speech_variables(field: str) -> None:
    with pytest.raises(ValidationError):
        DigitalHumanBinding(variables=[{"name": "value", "component_id": "kpi", "field": field}])


@pytest.mark.parametrize(
    "trigger",
    [
        {"kind": "interval"},
        {"kind": "interval", "interval_seconds": 1},
        {"kind": "threshold", "threshold": 10},
        {"kind": "parameter"},
        {"kind": "ranking_change"},
        {"kind": "status_change"},
    ],
)
def test_trigger_requires_bounded_settings(trigger: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        DigitalHumanTrigger.model_validate(trigger)


@pytest.mark.parametrize("kind", ["ranking_change", "status_change"])
def test_change_triggers_require_a_variable(kind: str) -> None:
    trigger = DigitalHumanTrigger.model_validate({"kind": kind, "variable": "rank"})
    assert trigger.variable == "rank"


def test_trigger_window_requires_a_complete_pair() -> None:
    trigger = DigitalHumanTrigger(kind="data_change", window_start="09:00", window_end="18:00")
    assert trigger.window_start == "09:00"
    with pytest.raises(ValidationError):
        DigitalHumanTrigger(kind="data_change", window_start="09:00")


def test_threshold_condition_groups_support_all_any_and_debounce() -> None:
    trigger = DigitalHumanTrigger.model_validate(
        {
            "kind": "threshold",
            "conditions": [
                {"variable": "sales", "operator": "gte", "value": 100},
                {"variable": "status", "operator": "eq", "value": "warning"},
            ],
            "condition_mode": "all",
            "priority": 10,
            "debounce_seconds": 5,
        }
    )
    assert trigger.conditions[0].operator == "gte"
    assert trigger.debounce_seconds == 5


@pytest.mark.parametrize(
    "patch",
    [
        {"kind": "threshold", "conditions": [{"variable": "sales", "operator": "gt"}]},
        {
            "kind": "threshold",
            "conditions": [{"variable": "sales", "operator": "exists", "value": 1}],
        },
        {
            "kind": "data_change",
            "conditions": [{"variable": "sales", "operator": "gt", "value": 1}],
        },
        {"kind": "threshold", "conditions": [{"variable": "sales", "operator": "gt", "value": []}]},
    ],
)
def test_invalid_threshold_condition_groups_are_rejected(patch: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        DigitalHumanTrigger.model_validate(patch)


@pytest.mark.parametrize(
    "command",
    [
        {"action": "mute", "enabled": "true"},
        {"action": "mute", "enabled": 1},
        {"action": "mute"},
        {"action": "setVolume", "volume": True},
        {"action": "setVolume", "volume": "0.5"},
        {"action": "setVolume", "volume": float("nan")},
        {"action": "play", "volume": 0.5},
        {"action": "speak", "text": "Unpublished text"},
    ],
)
def test_embed_speech_commands_reject_coercions_and_unpublished_content(command) -> None:
    with pytest.raises(ValidationError):
        DigitalHumanCommand.model_validate({"component_id": "speaker", **command})


@pytest.mark.parametrize(
    "name",
    [
        "digitalHumanReady",
        "statusChange",
        "speechStart",
        "speechEnd",
        "speechError",
        "fallback",
        "userGestureRequired",
    ],
)
def test_embed_speech_lifecycle_contract(name: str) -> None:
    event = DigitalHumanEvent(
        name=name,
        component_id="speaker",
        status="idle",
        task_id="task-1",
        source="host",
        code=None,
        request_id="query-1",
        timestamp=1000,
    )
    assert event.name == name


def test_embed_subtitle_cue_requires_complete_ordered_timing() -> None:
    event = DigitalHumanEvent(
        name="subtitleCue",
        component_id="speaker",
        status="speaking",
        task_id="task-1",
        source="host",
        code=None,
        request_id="query-1",
        timestamp=1000,
        cue_index=0,
        cue_text="Hello",
        cue_start=0,
        cue_end=1.25,
    )
    assert event.cue_end == 1.25


@pytest.mark.parametrize(
    "patch",
    [
        {"cue_index": 0},
        {"cue_text": "Hello"},
        {"cue_index": 0, "cue_text": "Hello", "cue_start": 1, "cue_end": 1},
        {"cue_index": -1, "cue_text": "Hello", "cue_start": 0, "cue_end": 1},
    ],
)
def test_embed_subtitle_cue_rejects_incomplete_or_invalid_timing(patch: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        DigitalHumanEvent(
            name="subtitleCue",
            component_id="speaker",
            status="speaking",
            task_id="task-1",
            source="host",
            code=None,
            request_id="query-1",
            timestamp=1000,
            **patch,
        )


@pytest.mark.parametrize(
    "patch",
    [
        {"asset_id": ""},
        {"sha256": "not-a-hash"},
        {"duration_seconds": float("nan")},
        {"transcript": "  "},
        {"subtitle_asset_id": "subtitle"},
        {"cues": [{"start": 1, "end": 1, "text": "Hello"}]},
        {"cues": [{"start": 0, "end": 5, "text": "Hello"}]},
        {"cues": [{"start": 0, "end": 1, "text": "Changed numbers 999"}]},
        {
            "cues": [
                {"start": 0, "end": 2, "text": "Hello"},
                {"start": 1, "end": 3, "text": "again"},
            ]
        },
    ],
)
def test_recording_contract_rejects_ambiguous_or_inconsistent_timeline(patch) -> None:
    with pytest.raises(ValidationError):
        SpeechRecording.model_validate(
            {
                "asset_id": "audio",
                "sha256": "a" * 64,
                "transcript": "Hello",
                "duration_seconds": 4,
                **patch,
            }
        )


def test_recording_supports_subsecond_cues_and_whitespace_between_sentences() -> None:
    recording = SpeechRecording.model_validate(
        {
            "asset_id": "audio",
            "sha256": "a" * 64,
            "transcript": "Hello again",
            "duration_seconds": 4,
            "cues": [
                {"start": 0.125, "end": 1, "text": "Hello"},
                {"start": 2, "end": 3.75, "text": "again"},
            ],
        }
    )
    assert recording.cues[0].start == 0.125
