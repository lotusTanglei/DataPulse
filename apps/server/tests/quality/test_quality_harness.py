from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPOSITORY_ROOT))


def _report(
    *,
    model: str,
    provider: str = "openai",
    run_date: str = "2026-09-23",
    success_rate: float = 1.0,
    binding_accuracy: float = 1.0,
    semantic_match_rate: float = 1.0,
    chart_rate: float = 1.0,
    draft_rate: float = 1.0,
    warnings: int = 0,
    average_ms: float = 120.0,
    cost_usd: float = 0.01,
    case_success: bool = True,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run": {
            "model": model,
            "provider": provider,
            "date": run_date,
            "fixture": "golden-v1",
        },
        "metrics": {
            "total_cases": 1,
            "successful_cases": int(case_success),
            "first_success_rate": success_rate,
            "failure_distribution": {} if case_success else {"AI_INVALID_OUTPUT": 1},
            "field_binding_accuracy": binding_accuracy,
            "field_bindings": {"correct": int(binding_accuracy == 1.0), "expected": 1},
            "semantic_match_rate": semantic_match_rate,
            "chart_type_reasonable_rate": chart_rate,
            "warning_count": warnings,
            "draft_produced_rate": draft_rate,
            "duration_ms": {"total": average_ms, "average": average_ms, "p95": average_ms},
            "token_cost": {"input_tokens": 10, "output_tokens": 5, "usd": cost_usd},
        },
        "cases": [
            {
                "case_id": "sales-by-region",
                "scenario": "销售",
                "success": case_success,
                "expected_bindings": ["区域", "销售额"],
                "actual_bindings": {"区域": "区域", "销售额": "销售额"}
                if binding_accuracy == 1.0
                else {"区域": "区域"},
                "expected_chart_types": ["bar"],
                "actual_chart_type": "bar" if chart_rate == 1.0 else "line",
                "warning_count": warnings,
                "duration_ms": int(average_ms),
                "input_tokens": 10,
                "output_tokens": 5,
                "error_code": None if case_success else "AI_INVALID_OUTPUT",
                "draft_produced": draft_rate == 1.0,
            }
        ],
    }


def _harness() -> Any:
    return importlib.import_module("tools.quality_harness")


def test_comparison_report_is_stable_across_multiple_providers_and_models() -> None:
    harness = _harness()
    reports = [
        _report(model="model-b", provider="provider-z"),
        _report(model="model-a", provider="provider-a"),
    ]

    comparison = harness.build_comparison(reports)

    assert comparison["schema_version"] == 1
    assert [run["key"] for run in comparison["runs"]] == [
        "provider-a/model-a/2026-09-23",
        "provider-z/model-b/2026-09-23",
    ]
    assert comparison["metrics"] == [
        "first_success_rate",
        "draft_produced_rate",
        "field_binding_accuracy",
        "semantic_match_rate",
        "chart_type_reasonable_rate",
        "failed_cases",
        "warning_count",
        "average_duration_ms",
        "cost_usd",
    ]


def test_upgrade_gate_blocks_when_any_controlled_metric_regresses() -> None:
    harness = _harness()
    baseline = _report(model="current")
    candidate = _report(model="candidate", binding_accuracy=0.5)

    decision = harness.evaluate_upgrade(baseline, candidate)

    assert decision["allowed"] is False
    assert decision["baseline_model"] == "current"
    assert decision["candidate_model"] == "candidate"
    assert decision["regressions"] == [
        {
            "metric": "field_binding_accuracy",
            "baseline": 1.0,
            "candidate": 0.5,
            "direction": "higher_is_better",
        }
    ]


def test_upgrade_gate_allows_candidate_with_no_regression() -> None:
    harness = _harness()
    baseline = _report(model="current")
    candidate = _report(model="candidate", average_ms=100.0, cost_usd=0.009)

    decision = harness.evaluate_upgrade(baseline, candidate)

    assert decision["allowed"] is True
    assert decision["regressions"] == []


def test_upgrade_gate_blocks_reports_with_incomparable_fixtures_or_cases() -> None:
    harness = _harness()
    baseline = _report(model="current")
    candidate = _report(model="candidate")
    candidate["schema_version"] = 2
    candidate["run"]["fixture"] = "golden-v2"
    candidate["cases"][0]["expected_bindings"] = ["区域"]

    decision = harness.evaluate_upgrade(baseline, candidate)

    assert decision["allowed"] is False
    assert decision["incompatibilities"] == [
        "schema_version mismatch: 1 != 2",
        "fixture mismatch: golden-v1 != golden-v2",
        "case sales-by-region expected_bindings mismatch",
    ]


def test_upgrade_gate_blocks_when_case_sets_differ() -> None:
    harness = _harness()
    baseline = _report(model="current")
    candidate = _report(model="candidate")
    candidate["cases"] = []

    decision = harness.evaluate_upgrade(baseline, candidate)

    assert decision["allowed"] is False
    assert decision["incompatibilities"] == ["case ids mismatch: ['sales-by-region'] != []"]


def test_upgrade_gate_blocks_unsupported_schema_and_missing_fixture() -> None:
    harness = _harness()
    baseline = _report(model="current")
    candidate = _report(model="candidate")
    baseline["schema_version"] = 2
    candidate["schema_version"] = 2
    baseline["run"].pop("fixture")
    candidate["run"].pop("fixture")

    decision = harness.evaluate_upgrade(baseline, candidate)

    assert decision["allowed"] is False
    assert decision["incompatibilities"] == [
        "unsupported baseline schema_version: 2",
        "unsupported candidate schema_version: 2",
        "unsupported baseline fixture: None",
        "unsupported candidate fixture: None",
    ]


def test_trend_dashboard_contains_ordered_runs_and_all_required_metrics() -> None:
    harness = _harness()
    reports = [
        _report(model="model-a", run_date="2026-09-23"),
        _report(model="model-a", run_date="2026-09-22", success_rate=0.9),
    ]

    trend = harness.build_trend(reports)
    html = harness.render_dashboard(trend)

    assert [point["date"] for point in trend["points"]] == ["2026-09-22", "2026-09-23"]
    assert "首次成功率" in html
    assert "语义匹配率" in html
    assert "平均耗时" in html
    assert "成本" in html
    assert "model-a" in html


def test_failure_samples_are_versioned_and_keep_reproduction_input() -> None:
    harness = _harness()
    report = _report(
        model="candidate",
        case_success=False,
        binding_accuracy=0.0,
        chart_rate=0.0,
        draft_rate=0.0,
    )

    samples = harness.build_failure_samples([report])

    assert samples["schema_version"] == 1
    assert samples["fixture_version"] == "golden-v1"
    assert samples["samples"] == [
        {
            "sample_id": "openai-candidate-sales-by-region",
            "source": {
                "provider": "openai",
                "model": "candidate",
                "date": "2026-09-23",
            },
            "case_id": "sales-by-region",
            "scenario": "销售",
            "expected_bindings": ["区域", "销售额"],
            "expected_chart_types": ["bar"],
            "actual_bindings": {"区域": "区域"},
            "actual_chart_type": "line",
            "error_code": "AI_INVALID_OUTPUT",
            "draft_produced": False,
            "failure_reasons": [
                "generation_failed",
                "binding_mismatch",
                "chart_type_mismatch",
                "draft_missing",
            ],
        }
    ]


def test_upgrade_gate_cli_returns_nonzero_and_writes_decision(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "decision.json"
    baseline_path.write_text(json.dumps(_report(model="current")), encoding="utf-8")
    candidate_path.write_text(
        json.dumps(_report(model="candidate", success_rate=0.0, case_success=False)),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "tools/run_model_upgrade_gate.py",
            "--",
            "--baseline",
            str(baseline_path),
            "--candidate",
            str(candidate_path),
            "--output",
            str(output_path),
        ],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert json.loads(output_path.read_text(encoding="utf-8"))["allowed"] is False


def test_harness_cli_writes_comparison_dashboard_and_failure_library(tmp_path: Path) -> None:
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    comparison_path = tmp_path / "comparison.json"
    trend_path = tmp_path / "trend.json"
    dashboard_path = tmp_path / "dashboard.html"
    failures_path = tmp_path / "failures.json"
    first_path.write_text(json.dumps(_report(model="model-a")), encoding="utf-8")
    second_path.write_text(
        json.dumps(_report(model="model-b", case_success=False, success_rate=0.0)),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "tools/run_quality_harness.py",
            "--",
            "--report",
            str(first_path),
            "--report",
            str(second_path),
            "--comparison-output",
            str(comparison_path),
            "--trend-output",
            str(trend_path),
            "--dashboard-output",
            str(dashboard_path),
            "--failures-output",
            str(failures_path),
        ],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(completed.stdout)
    assert summary == {"failures": 1, "reports": 2}
    assert len(json.loads(comparison_path.read_text(encoding="utf-8"))["runs"]) == 2
    assert len(json.loads(trend_path.read_text(encoding="utf-8"))["points"]) == 2
    assert "DataPulse 质量趋势" in dashboard_path.read_text(encoding="utf-8")
    assert len(json.loads(failures_path.read_text(encoding="utf-8"))["samples"]) == 1
