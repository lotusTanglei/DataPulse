from __future__ import annotations

import csv
import json
import math
import os
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Protocol

import httpx

GOLDEN_VERSION = "golden-v1"
PRICING_USD_PER_MILLION: dict[str, tuple[float, float]] = {
    "gpt-6-astra": (10.0, 50.0),
}
MAX_REAL_REQUESTS = 8
INPUT_FRAMING_TOKEN_ALLOWANCE = 1024
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
    cost_audit: dict[str, Any] | None = None


class EvaluationProvider(Protocol):
    def run(self, case: GoldenCase) -> ProviderResult: ...


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


def _error_result(
    code: str, elapsed_ms: int, *, input_tokens: int = 0, output_tokens: int = 0
) -> ProviderResult:
    return ProviderResult(
        success=False,
        bindings={},
        chart_type=None,
        warning_count=0,
        duration_ms=elapsed_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
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
        budget_usd: str | Decimal = "1.00",
        max_output_tokens: int = 512,
    ) -> None:
        try:
            budget = Decimal(str(budget_usd))
        except InvalidOperation as error:
            raise ValueError("budget_usd must be greater than 0 and at most 1.00") from error
        if not budget.is_finite() or not 0 < budget <= Decimal("1.00"):
            raise ValueError("budget_usd must be greater than 0 and at most 1.00")
        if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 4096:
            raise ValueError("max_output_tokens must be an integer between 1 and 4096")
        prices = PRICING_USD_PER_MILLION.get(model)
        if prices is None:
            raise ValueError(f"pricing is not configured for model: {model}")
        self._input_price, self._output_price = (Decimal(str(price)) for price in prices)
        if any(
            not price.is_finite() or price < 0 for price in (self._input_price, self._output_price)
        ):
            raise ValueError(f"invalid pricing for model: {model}")
        self.model = model
        self._budget = budget
        self._max_output_tokens = max_output_tokens
        self._accounted = Decimal(0)
        self._reported_cost = Decimal(0)
        self._usage_complete = True
        self._request_count = 0
        self._halted_reason: str | None = None
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
            "max_tokens": self._max_output_tokens,
        }

    def _cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        return (input_tokens * self._input_price + output_tokens * self._output_price) / 1_000_000

    def budget_summary(self) -> dict[str, Any]:
        return {
            "limit_usd": float(self._budget),
            "max_output_tokens": self._max_output_tokens,
            "max_requests": MAX_REAL_REQUESTS,
            "requests_attempted": self._request_count,
            "input_bound": "request_utf8_bytes_plus_framing_allowance",
            "framing_token_allowance": INPUT_FRAMING_TOKEN_ALLOWANCE,
            "pricing_usd_per_million": {
                "input": float(self._input_price),
                "output": float(self._output_price),
            },
            "accounted_usd": float(self._accounted),
            "reported_cost_usd": float(self._reported_cost) if self._usage_complete else None,
            "remaining_usd": float(self._budget - self._accounted),
            "usage_complete": self._usage_complete,
            "within_limit": self._accounted <= self._budget,
            "halted_reason": self._halted_reason,
            "assurance": "conditional_provider_limits_and_pricing",
        }

    def _audited(
        self,
        result: ProviderResult,
        *,
        requested: bool,
        input_bound: int = 0,
        reservation: Decimal = Decimal(0),
        actual_cost: Decimal | None = None,
    ) -> ProviderResult:
        return replace(
            result,
            cost_audit={
                "requested": requested,
                "input_token_upper_bound": input_bound,
                "max_output_tokens": self._max_output_tokens,
                "reserved_usd": float(reservation),
                "reported_cost_usd": float(actual_cost) if actual_cost is not None else None,
                "usage_status": "reported"
                if actual_cost is not None
                else ("unknown" if requested else "not_requested"),
                "accounted_usd_after_case": float(self._accounted),
                "remaining_usd_after_case": float(self._budget - self._accounted),
            },
        )

    def run(self, case: GoldenCase) -> ProviderResult:
        started = time.perf_counter()
        if self._halted_reason:
            return self._audited(
                _error_result("AI_BUDGET_HALTED", _elapsed_ms(started)), requested=False
            )
        if self._request_count >= MAX_REAL_REQUESTS:
            self._halted_reason = "AI_REQUEST_LIMIT"
            return self._audited(
                _error_result("AI_REQUEST_LIMIT", _elapsed_ms(started)), requested=False
            )
        body = json.dumps(
            self._request_payload(case), ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        input_bound = len(body) + INPUT_FRAMING_TOKEN_ALLOWANCE
        reservation = self._cost(input_bound, self._max_output_tokens)
        if reservation > self._budget - self._accounted:
            self._halted_reason = "AI_BUDGET_EXCEEDED"
            return self._audited(
                _error_result("AI_BUDGET_EXCEEDED", _elapsed_ms(started)),
                requested=False,
                input_bound=input_bound,
            )
        self._accounted += reservation
        self._request_count += 1
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

        def uncertain(code: str) -> ProviderResult:
            # A timeout/error may still be billable. Never refund its reservation or retry.
            self._usage_complete = False
            self._halted_reason = code
            return self._audited(
                _error_result(code, _elapsed_ms(started)),
                requested=True,
                input_bound=input_bound,
                reservation=reservation,
            )

        try:
            response = self._client.post(self._endpoint, headers=headers, content=body)
        except httpx.TimeoutException:
            return uncertain("AI_TIMEOUT")
        except httpx.HTTPError:
            return uncertain("AI_UNAVAILABLE")
        if response.status_code == 429:
            return uncertain("AI_RATE_LIMITED")
        if 500 <= response.status_code:
            return uncertain("AI_PROVIDER_5XX")
        if 400 <= response.status_code:
            return uncertain("AI_PROVIDER_4XX")
        try:
            envelope = response.json()
        except ValueError:
            return uncertain("AI_USAGE_INVALID")
        usage = envelope.get("usage") if isinstance(envelope, dict) else None
        if not isinstance(usage, dict):
            return uncertain("AI_USAGE_INVALID")
        input_tokens = usage.get("prompt_tokens", usage.get("input_tokens"))
        output_tokens = usage.get("completion_tokens", usage.get("output_tokens"))
        if any(type(count) is not int or count < 0 for count in (input_tokens, output_tokens)):
            return uncertain("AI_USAGE_INVALID")
        if "total_tokens" in usage and (
            type(usage["total_tokens"]) is not int
            or usage["total_tokens"] != input_tokens + output_tokens
        ):
            return uncertain("AI_USAGE_INVALID")
        actual_cost = self._cost(input_tokens, output_tokens)
        self._accounted += actual_cost - reservation
        self._reported_cost += actual_cost

        def audited(result: ProviderResult) -> ProviderResult:
            return self._audited(
                result,
                requested=True,
                input_bound=input_bound,
                reservation=reservation,
                actual_cost=actual_cost,
            )

        if input_tokens > input_bound or output_tokens > self._max_output_tokens:
            self._halted_reason = "AI_USAGE_EXCEEDS_RESERVATION"
            return audited(
                _error_result(
                    self._halted_reason,
                    _elapsed_ms(started),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            )
        try:
            content = envelope["choices"][0]["message"]["content"]
            payload = json.loads(content)
            if not isinstance(payload, dict):
                raise ValueError("model output is not an object")
        except (KeyError, IndexError, TypeError, ValueError):
            return audited(
                _error_result(
                    "AI_INVALID_OUTPUT",
                    _elapsed_ms(started),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            )
        bindings = payload.get("bindings", {})
        if not isinstance(bindings, dict):
            bindings = {}
        return audited(
            ProviderResult(
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
        )


def _elapsed_ms(started: float) -> int:
    return max(1, round((time.perf_counter() - started) * 1000))


def _cost_usd(input_tokens: int, output_tokens: int, model: str) -> float:
    prices = PRICING_USD_PER_MILLION.get(model)
    if prices is None:
        raise ValueError(f"pricing is not configured for model: {model}")
    input_price, output_price = prices
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
    semantic_matches = sum(
        all(result.bindings.get(field) == field for field in case.expected_bindings)
        and result.chart_type in case.expected_chart_types
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
        "semantic_match_rate": round(semantic_matches / total, 6),
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
                **({"cost_audit": result.cost_audit} if result.cost_audit is not None else {}),
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
    budget_usd: str | Decimal = "1.00",
    max_output_tokens: int = 512,
) -> dict[str, Any]:
    cases = load_golden_cases(fixture_root)
    provider: EvaluationProvider
    close_provider = False
    if provider_name == "fixture":
        provider = FixtureProvider()
    elif provider_name == "openai":
        if len(cases) > MAX_REAL_REQUESTS:
            raise ValueError(f"real baseline is limited to {MAX_REAL_REQUESTS} cases")
        if not base_url or not api_key:
            raise ValueError("openai provider requires base_url and api_key")
        provider = OpenAICompatibleProvider(
            base_url=base_url,
            api_key=api_key,
            model=model,
            budget_usd=budget_usd,
            max_output_tokens=max_output_tokens,
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
    report = build_report(cases, results, model=model, provider=provider_name, run_date=run_date)
    if isinstance(provider, OpenAICompatibleProvider):
        report["budget"] = provider.budget_summary()
        report["metrics"]["token_cost"].update(
            {
                "usd": report["budget"]["accounted_usd"],
                "basis": "reported_usage_or_retained_reservation",
                "reported_cost_usd": report["budget"]["reported_cost_usd"],
                "usage_complete": report["budget"]["usage_complete"],
            }
        )
    return report


def default_run_date() -> str:
    return datetime.now(UTC).date().isoformat()


def environment_defaults() -> dict[str, str | None]:
    return {
        "base_url": os.environ.get("DATAPULSE_AI_BASE_URL"),
        "api_key": os.environ.get("DATAPULSE_AI_API_KEY"),
        "model": os.environ.get("DATAPULSE_AI_MODEL", "gpt-6-astra"),
    }
