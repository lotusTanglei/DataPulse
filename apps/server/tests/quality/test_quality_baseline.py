from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.quality_baseline import (  # noqa: E402
    FixtureProvider,
    GoldenCase,
    OpenAICompatibleProvider,
    aggregate_results,
    build_report,
    load_golden_cases,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
GOLDEN_ROOT = REPOSITORY_ROOT / "fixtures" / "golden"


def test_golden_fixture_covers_required_scenarios_and_dirty_chinese_data() -> None:
    cases = load_golden_cases(GOLDEN_ROOT)

    assert {case.scenario for case in cases} == {"经营", "运营", "销售", "设备"}
    assert {case.table_kind for case in cases} == {"single", "wide"}
    assert len(cases) >= 8
    assert any("日期" in case.fields for case in cases)
    assert any("金额" in case.fields or "销售额" in case.fields for case in cases)
    assert any(case.dirty_values for case in cases)
    assert any(case.mixed_types for case in cases)


def test_fixture_provider_returns_expected_bindings_and_chart_types() -> None:
    cases = load_golden_cases(GOLDEN_ROOT)
    results = [FixtureProvider().run(case) for case in cases]

    assert all(result.success for result in results)
    assert all(result.draft_produced for result in results)
    assert all(result.error_code is None for result in results)
    for case, result in zip(cases, results, strict=True):
        assert result.bindings == {field: field for field in case.expected_bindings}
        assert result.chart_type == case.expected_chart_types[0]


def test_metrics_include_success_failure_binding_chart_latency_and_cost() -> None:
    cases = [
        GoldenCase(
            case_id="a",
            scenario="经营",
            dataset_path="data.csv",
            question="按区域查看销售额",
            fields=("区域", "销售额"),
            rows=(),
            table_kind="single",
            expected_bindings=("区域", "销售额"),
            expected_chart_types=("bar",),
            dirty_values=(),
            mixed_types=(),
        ),
        GoldenCase(
            case_id="b",
            scenario="运营",
            dataset_path="data.csv",
            question="查看活跃用户趋势",
            fields=("日期", "活跃用户"),
            rows=(),
            table_kind="single",
            expected_bindings=("日期", "活跃用户"),
            expected_chart_types=("line",),
            dirty_values=(),
            mixed_types=(),
        ),
    ]
    provider = FixtureProvider(fail_case_ids={"b"})
    metrics = aggregate_results(cases, [provider.run(case) for case in cases])

    assert metrics["total_cases"] == 2
    assert metrics["first_success_rate"] == 0.5
    assert metrics["failure_distribution"] == {"AI_INVALID_OUTPUT": 1}
    assert metrics["field_binding_accuracy"] == 1.0
    assert metrics["chart_type_reasonable_rate"] == 1.0
    assert metrics["warning_count"] == 0
    assert metrics["duration_ms"]["total"] == 26
    assert metrics["token_cost"]["input_tokens"] > 0
    assert metrics["token_cost"]["output_tokens"] > 0
    assert metrics["token_cost"]["usd"] > 0


def test_openai_provider_collects_usage_for_metric_cost() -> None:
    case = load_golden_cases(GOLDEN_ROOT)[0]

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["response_format"] == {"type": "json_object"}
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "success": True,
                                    "bindings": {field: field for field in case.expected_bindings},
                                    "chart_type": case.expected_chart_types[0],
                                    "warning_count": 1,
                                    "draft_produced": True,
                                }
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 31, "completion_tokens": 13},
            },
            request=request,
        )

    provider = OpenAICompatibleProvider(
        base_url="https://provider.example/v1",
        api_key="test-key",
        model="gpt-6-astra",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    try:
        result = provider.run(case)
    finally:
        provider.close()

    assert result.success is True
    assert result.input_tokens == 31
    assert result.output_tokens == 13
    assert result.warning_count == 1
    assert result.duration_ms >= 1


def test_openai_provider_classifies_rate_limit_without_retry() -> None:
    case = load_golden_cases(GOLDEN_ROOT)[0]
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, request=request)

    provider = OpenAICompatibleProvider(
        base_url="https://provider.example/v1",
        api_key="test-key",
        model="gpt-6-astra",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    try:
        result = provider.run(case)
    finally:
        provider.close()

    assert result.error_code == "AI_RATE_LIMITED"
    assert result.success is False
    assert calls == 1


def test_report_contract_is_stable_and_sorted() -> None:
    cases = load_golden_cases(GOLDEN_ROOT)
    results = [FixtureProvider().run(case) for case in reversed(cases)]
    report = build_report(
        cases,
        results,
        model="gpt-6-astra",
        provider="fixture",
        run_date="2026-09-22",
    )

    assert report["schema_version"] == 1
    assert report["run"] == {
        "model": "gpt-6-astra",
        "provider": "fixture",
        "date": "2026-09-22",
        "fixture": "golden-v1",
    }
    assert [item["case_id"] for item in report["cases"]] == sorted(
        item["case_id"] for item in report["cases"]
    )
    json.dumps(report, ensure_ascii=False)


def test_archived_baseline_records_model_date_and_numeric_values() -> None:
    report_path = (
        REPOSITORY_ROOT
        / "test-evidence"
        / "quality-baseline"
        / "baseline-2026-09-22.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["run"]["model"] == "gpt-6-astra"
    assert report["run"]["date"] == "2026-09-22"
    assert report["metrics"]["total_cases"] == 8
    assert isinstance(report["metrics"]["first_success_rate"], float)
    assert isinstance(report["metrics"]["field_binding_accuracy"], float)
    assert isinstance(report["metrics"]["duration_ms"]["average"], float)
    assert isinstance(report["metrics"]["token_cost"]["usd"], float)


@pytest.mark.parametrize("repeat", [1, 2])
def test_one_command_rerun_writes_reproducible_fixture_report(tmp_path: Path, repeat: int) -> None:
    output = tmp_path / "baseline.json"
    command = [
        sys.executable,
        "tools/run_quality_baseline.py",
        "--provider",
        "fixture",
        "--date",
        "2026-09-22",
        "--output",
        str(output),
    ]
    first = subprocess.run(command, cwd=REPOSITORY_ROOT, check=True, capture_output=True, text=True)
    first_payload = json.loads(first.stdout)
    first_bytes = output.read_bytes()
    second = subprocess.run(
        command, cwd=REPOSITORY_ROOT, check=True, capture_output=True, text=True
    )
    second_payload = json.loads(second.stdout)

    assert second_payload == first_payload
    assert output.read_bytes() == first_bytes
    assert first_payload["run"]["date"] == "2026-09-22"
