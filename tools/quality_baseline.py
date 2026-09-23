from __future__ import annotations

import csv
import json
import math
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import httpx

GOLDEN_VERSION = "golden-v1"
PRICING_USD_PER_MILLION: dict[str, tuple[float, float]] = {
    "gpt-6-astra": (10.0, 50.0),
}
_DIRTY_MARKERS = {
    "",
    "-",
    "n/a",
    "na",
    "null",
    "unknown",
    "bad-date",
    "bad-time",
    "待核实",
    "待确认",
    "缺失",
    "脏数据",
    "数据异常",
    "超时",
    "未知",
}


@dataclass(frozen=True)
class GoldenDataset:
    scenario: str
    dataset_path: str
    table_kind: str
    fields: tuple[str, ...]
    rows: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class GoldenCase:
    case_id: str
    scenario: str
    dataset_path: str
    question: str
    fields: tuple[str, ...]
    rows: tuple[dict[str, str], ...]
    table_kind: str
    expected_bindings: tuple[str, ...]
    expected_chart_types: tuple[str, ...]
    dirty_values: tuple[str, ...]
    mixed_types: tuple[str, ...]


@dataclass(frozen=True)
class ProviderResult:
    success: bool
    bindings: dict[str, str]
    chart_type: str | None
    warning_count: int
    duration_ms: int
    input_tokens: int
    output_tokens: int
    error_code: str | None
    draft_produced: bool


class EvaluationProvider(Protocol):
    def run(self, case: GoldenCase) -> ProviderResult:
        ...


def _is_numeric(value: str) -> bool:
    try:
        float(value.replace(",", ""))
    except ValueError:
        return False
    return value.strip() != ""


def _dataset_properties(
    rows: tuple[dict[str, str], ...], fields: tuple[str, ...]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    dirty: set[str] = set()
    mixed: set[str] = set()
    for field in fields:
        values = [str(row.get(field, "")).strip() for row in rows]
        dirty.update(value for value in values if value.lower() in _DIRTY_MARKERS)
        non_empty = [value for value in values if value != ""]
        if any(_is_numeric(value) for value in non_empty) and any(
            not _is_numeric(value) for value in non_empty
        ):
            mixed.add(field)
    return tuple(sorted(dirty)), tuple(sorted(mixed))


def load_golden_cases(fixture_root: Path) -> tuple[GoldenCase, ...]:
    manifest_path = fixture_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("version") != GOLDEN_VERSION:
        raise ValueError(f"unsupported golden fixture version: {manifest.get('version')!r}")
    cases: list[GoldenCase] = []
    for dataset_spec in manifest.get("datasets", []):
        scenario = str(dataset_spec["scenario"])
        dataset_path = str(dataset_spec["path"])
        table_kind = str(dataset_spec["table_kind"])
        csv_path = fixture_root / dataset_path
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = tuple(reader.fieldnames or ())
            rows = tuple({field: str(row.get(field, "")) for field in fields} for row in reader)
        dirty_values, mixed_types = _dataset_properties(rows, fields)
        for case_spec in dataset_spec.get("cases", []):
            cases.append(
                GoldenCase(
                    case_id=str(case_spec["case_id"]),
                    scenario=scenario,
                    dataset_path=dataset_path,
                    question=str(case_spec["question"]),
                    fields=fields,
                    rows=rows,
                    table_kind=table_kind,
                    expected_bindings=tuple(str(item) for item in case_spec["expected_bindings"]),
                    expected_chart_types=tuple(
                        str(item) for item in case_spec["expected_chart_types"]
                    ),
                    dirty_values=dirty_values,
                    mixed_types=mixed_types,
                )
            )
    if not cases:
        raise ValueError("golden fixture has no evaluation cases")
    return tuple(sorted(cases, key=lambda case: case.case_id))


def _fixture_duration(case_id: str) -> int:
    return 10 + sum(case_id.encode("utf-8")) % 7


class FixtureProvider:
    def __init__(self, *, fail_case_ids: set[str] | None = None) -> None:
        self._fail_case_ids = frozenset(fail_case_ids or ())

    def run(self, case: GoldenCase) -> ProviderResult:
        failed = case.case_id in self._fail_case_ids
        return ProviderResult(
            success=not failed,
            bindings={field: field for field in case.expected_bindings},
            chart_type=case.expected_chart_types[0],
            warning_count=0,
            duration_ms=_fixture_duration(case.case_id),
            input_tokens=120 + len(case.question),
            output_tokens=48 + len(case.expected_bindings) * 8,
            error_code="AI_INVALID_OUTPUT" if failed else None,
            draft_produced=True,
        )


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _error_result(code: str, elapsed_ms: int, *, input_tokens: int = 0) -> ProviderResult:
    return ProviderResult(
        success=False,
        bindings={},
        chart_type=None,
        warning_count=0,
        duration_ms=elapsed_ms,
        input_tokens=input_tokens,
        output_tokens=0,
        error_code=code,
        draft_produced=False,
    )


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 120,
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self._endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self._client = client or httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout_seconds
        )
        self._api_key = api_key

    def close(self) -> None:
        self._client.close()

    def _request_payload(self, case: GoldenCase) -> dict[str, Any]:
        sample = [dict(row) for row in case.rows[:5]]
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return JSON only with success, bindings, chart_type, warning_count, "
                        "error_code, and draft_produced. Use only fields in the dataset."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "scenario": case.scenario,
                            "question": case.question,
                            "fields": case.fields,
                            "sample_rows": sample,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
        }

    def run(self, case: GoldenCase) -> ProviderResult:
        started = time.perf_counter()
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            response = self._client.post(
                self._endpoint, headers=headers, json=self._request_payload(case)
            )
        except httpx.TimeoutException:
            return _error_result("AI_TIMEOUT", _elapsed_ms(started))
        except httpx.HTTPError:
            return _error_result("AI_UNAVAILABLE", _elapsed_ms(started))
        if response.status_code == 429:
            return _error_result("AI_RATE_LIMITED", _elapsed_ms(started))
        if 500 <= response.status_code:
            return _error_result("AI_PROVIDER_5XX", _elapsed_ms(started))
        if 400 <= response.status_code:
            return _error_result("AI_PROVIDER_4XX", _elapsed_ms(started))
        try:
            envelope = response.json()
            content = envelope["choices"][0]["message"]["content"]
            payload = json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError):
            return _error_result("AI_INVALID_OUTPUT", _elapsed_ms(started))
        usage = envelope.get("usage", {})
        input_tokens = _safe_int(usage.get("prompt_tokens", usage.get("input_tokens", 0)))
        output_tokens = _safe_int(usage.get("completion_tokens", usage.get("output_tokens", 0)))
        bindings = payload.get("bindings", {})
        if not isinstance(bindings, dict):
            bindings = {}
        return ProviderResult(
            success=bool(payload.get("success", True)),
            bindings={str(key): str(value) for key, value in bindings.items()},
            chart_type=str(payload["chart_type"]) if payload.get("chart_type") else None,
            warning_count=_safe_int(payload.get("warning_count", 0)),
            duration_ms=_elapsed_ms(started),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error_code=str(payload["error_code"]) if payload.get("error_code") else None,
            draft_produced=bool(payload.get("draft_produced", False)),
        )


def _elapsed_ms(started: float) -> int:
    return max(1, round((time.perf_counter() - started) * 1000))


def _cost_usd(input_tokens: int, output_tokens: int, model: str) -> float:
    input_price, output_price = PRICING_USD_PER_MILLION.get(model, (0.0, 0.0))
    return round((input_tokens * input_price + output_tokens * output_price) / 1_000_000, 6)


def aggregate_results(
    cases: tuple[GoldenCase, ...] | list[GoldenCase],
    results: tuple[ProviderResult, ...] | list[ProviderResult],
    *,
    model: str = "gpt-6-astra",
) -> dict[str, Any]:
    if len(cases) != len(results) or not cases:
        raise ValueError("cases and results must have the same non-zero length")
    total = len(cases)
    successes = sum(result.success for result in results)
    expected_binding_count = sum(len(case.expected_bindings) for case in cases)
    correct_bindings = sum(
        sum(result.bindings.get(field) == field for field in case.expected_bindings)
        for case, result in zip(cases, results, strict=True)
    )
    reasonable_charts = sum(
        result.chart_type in case.expected_chart_types
        for case, result in zip(cases, results, strict=True)
    )
    failures: dict[str, int] = {}
    for result in results:
        if result.error_code:
            failures[result.error_code] = failures.get(result.error_code, 0) + 1
    durations = sorted(result.duration_ms for result in results)
    p95_index = min(len(durations) - 1, max(0, math.ceil(len(durations) * 0.95) - 1))
    input_tokens = sum(result.input_tokens for result in results)
    output_tokens = sum(result.output_tokens for result in results)
    return {
        "total_cases": total,
        "successful_cases": successes,
        "first_success_rate": round(successes / total, 6),
        "failure_distribution": dict(sorted(failures.items())),
        "field_binding_accuracy": round(correct_bindings / expected_binding_count, 6)
        if expected_binding_count
        else 1.0,
        "field_bindings": {"correct": correct_bindings, "expected": expected_binding_count},
        "chart_type_reasonable_rate": round(reasonable_charts / total, 6),
        "warning_count": sum(result.warning_count for result in results),
        "draft_produced_rate": round(sum(result.draft_produced for result in results) / total, 6),
        "duration_ms": {
            "total": sum(durations),
            "average": round(sum(durations) / total, 3),
            "p95": durations[p95_index],
        },
        "token_cost": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "usd": _cost_usd(input_tokens, output_tokens, model),
        },
    }


def build_report(
    cases: tuple[GoldenCase, ...] | list[GoldenCase],
    results: tuple[ProviderResult, ...] | list[ProviderResult],
    *,
    model: str,
    provider: str,
    run_date: str,
) -> dict[str, Any]:
    ordered = sorted(zip(cases, results, strict=True), key=lambda item: item[0].case_id)
    ordered_cases = tuple(item[0] for item in ordered)
    ordered_results = tuple(item[1] for item in ordered)
    return {
        "schema_version": 1,
        "run": {"model": model, "provider": provider, "date": run_date, "fixture": GOLDEN_VERSION},
        "metrics": aggregate_results(ordered_cases, ordered_results, model=model),
        "cases": [
            {
                "case_id": case.case_id,
                "scenario": case.scenario,
                "success": result.success,
                "expected_bindings": list(case.expected_bindings),
                "actual_bindings": dict(sorted(result.bindings.items())),
                "expected_chart_types": list(case.expected_chart_types),
                "actual_chart_type": result.chart_type,
                "warning_count": result.warning_count,
                "duration_ms": result.duration_ms,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "error_code": result.error_code,
                "draft_produced": result.draft_produced,
            }
            for case, result in ordered
        ],
    }


def write_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_baseline(
    *,
    provider_name: str,
    fixture_root: Path,
    model: str,
    run_date: str,
    base_url: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    cases = load_golden_cases(fixture_root)
    provider: EvaluationProvider
    close_provider = False
    if provider_name == "fixture":
        provider = FixtureProvider()
    elif provider_name == "openai":
        if not base_url or not api_key:
            raise ValueError("openai provider requires base_url and api_key")
        provider = OpenAICompatibleProvider(
            base_url=base_url,
            api_key=api_key,
            model=model,
        )
        close_provider = True
    else:
        raise ValueError(f"unsupported provider: {provider_name}")
    try:
        results = [provider.run(case) for case in cases]
    finally:
        if close_provider:
            assert isinstance(provider, OpenAICompatibleProvider)
            provider.close()
    return build_report(cases, results, model=model, provider=provider_name, run_date=run_date)


def default_run_date() -> str:
    return datetime.now(UTC).date().isoformat()


def environment_defaults() -> dict[str, str | None]:
    return {
        "base_url": os.environ.get("DATAPULSE_AI_BASE_URL"),
        "api_key": os.environ.get("DATAPULSE_AI_API_KEY"),
        "model": os.environ.get("DATAPULSE_AI_MODEL", "gpt-6-astra"),
    }
