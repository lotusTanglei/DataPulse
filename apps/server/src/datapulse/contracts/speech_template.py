"""Bounded placeholder grammar shared by validation and speech planning."""

import re
from dataclasses import dataclass

MAX_TEMPLATE_LENGTH = 4000
MAX_VARIABLES = 50
_TOKEN = re.compile(
    r"(?P<name>[\w.-]+)(?:\s*\|\s*(?P<format>number|percent|currency|date|enum|rank|trend|number_zh|text)"
    r'(?:\s*:\s*"(?P<option>[^"{}\r\n]{1,32})")?)?',
)
_NUMBER = re.compile(r"[+]?0(?:\.0{1,8})?a?")
_SENSITIVE = re.compile(
    r"(?:^|[^a-z0-9])(?:password|passwd|secret|token|api[_-]?key|credential|phone|mobile|telephone|tel|email|ssn)"
    r"(?:$|[^a-z0-9])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SpeechPlaceholder:
    start: int
    end: int
    name: str
    format: str
    option: str | None


def sensitive_speech_field(name: str) -> bool:
    # Normalize camelCase before applying token boundaries so naming style
    # cannot bypass the speech data allowlist.
    normalized = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    if any(marker in normalized for marker in ("身份证", "手机号", "电话", "邮箱")):
        return True
    return bool(_SENSITIVE.search(normalized))


def parse_speech_template(template: str) -> tuple[SpeechPlaceholder, ...]:
    if not template.strip() or len(template) > MAX_TEMPLATE_LENGTH:
        raise ValueError("Speech templates must contain 1 to 4000 characters.")
    tokens: list[SpeechPlaceholder] = []
    offset = 0
    while offset < len(template):
        start = template.find("{{", offset)
        closing = template.find("}}", offset)
        if start == -1:
            if closing != -1:
                raise ValueError("Unexpected closing placeholder delimiter.")
            break
        if closing == -1 or closing < start:
            raise ValueError("Unclosed speech placeholder.")
        match = _TOKEN.fullmatch(template[start + 2 : closing].strip())
        if match is None:
            raise ValueError("Invalid speech placeholder or formatter.")
        name, formatter, option = match.group("name", "format", "option")
        if any(part in {"__proto__", "constructor", "prototype"} for part in name.split(".")):
            raise ValueError("Invalid speech variable name.")
        if formatter in {"number", "percent"} and option and not _NUMBER.fullmatch(option):
            raise ValueError("Invalid speech number format.")
        if formatter == "currency" and option and not re.fullmatch(r"[A-Z]{3}", option):
            raise ValueError("Invalid speech currency code.")
        if formatter == "date" and option not in {None, "date", "time", "datetime"}:
            raise ValueError("Invalid speech date format.")
        if formatter in {"enum", "rank", "trend", "number_zh", "text"} and option is not None:
            raise ValueError("This speech formatter does not accept options.")
        tokens.append(SpeechPlaceholder(start, closing + 2, name, formatter or "text", option))
        if len(tokens) > MAX_VARIABLES:
            raise ValueError("Speech templates allow at most 50 placeholders.")
        offset = closing + 2
    return tuple(tokens)
