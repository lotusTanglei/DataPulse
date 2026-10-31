from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

HIGHER_IS_BETTER = (
    "first_success_rate",
    "draft_produced_rate",
    "field_binding_accuracy",
    "semantic_match_rate",
    "chart_type_reasonable_rate",
)
LOWER_IS_BETTER = (
    "failed_cases",
    "warning_count",
    "average_duration_ms",
    "cost_usd",
)
CONTROLLED_METRICS = HIGHER_IS_BETTER + LOWER_IS_BETTER
SUPPORTED_SCHEMA_VERSION = 1

_METRIC_LABELS = {
    "first_success_rate": "首次成功率",
    "draft_produced_rate": "草稿产出率",
    "field_binding_accuracy": "字段绑定准确率",
    "semantic_match_rate": "语义匹配率",
    "chart_type_reasonable_rate": "图表合理率",
    "failed_cases": "失败数",
    "warning_count": "警告数",
    "average_duration_ms": "平均耗时 (ms)",
    "cost_usd": "成本 (USD)",
}


def read_report(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError(f"quality report must be an object: {path}")
    _report_identity(report)
    _metric_values(report)
    return report


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _report_identity(report: dict[str, Any]) -> tuple[str, str, str]:
    run = report.get("run")
    if not isinstance(run, dict):
        raise ValueError("quality report is missing run metadata")
    try:
        return str(run["provider"]), str(run["model"]), str(run["date"])
    except KeyError as error:
        raise ValueError(f"quality report is missing run.{error.args[0]}") from error


def _number(value: object, path: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"quality report metric {path} must be numeric")
    return value


def _metric_values(report: dict[str, Any]) -> dict[str, int | float]:
    metrics = report.get("metrics")
    if not isinstance(metrics, dict):
        raise ValueError("quality report is missing metrics")
    duration = metrics.get("duration_ms")
    token_cost = metrics.get("token_cost")
    if not isinstance(duration, dict) or not isinstance(token_cost, dict):
        raise ValueError("quality report is missing duration or cost metrics")
    total = _number(metrics.get("total_cases"), "total_cases")
    successful = _number(metrics.get("successful_cases"), "successful_cases")
    values = {
        "first_success_rate": _number(
            metrics.get("first_success_rate"), "first_success_rate"
        ),
        "draft_produced_rate": _number(
            metrics.get("draft_produced_rate"), "draft_produced_rate"
        ),
        "field_binding_accuracy": _number(
            metrics.get("field_binding_accuracy"), "field_binding_accuracy"
        ),
        "semantic_match_rate": _number(
            metrics.get("semantic_match_rate"), "semantic_match_rate"
        ),
        "chart_type_reasonable_rate": _number(
            metrics.get("chart_type_reasonable_rate"), "chart_type_reasonable_rate"
        ),
        "failed_cases": total - successful,
        "warning_count": _number(metrics.get("warning_count"), "warning_count"),
        "average_duration_ms": _number(duration.get("average"), "duration_ms.average"),
        "cost_usd": _number(token_cost.get("usd"), "token_cost.usd"),
    }
    return values


def build_comparison(reports: list[dict[str, Any]]) -> dict[str, Any]:
    if len(reports) < 2:
        raise ValueError("comparison requires at least two quality reports")
    runs = []
    for report in reports:
        provider, model, run_date = _report_identity(report)
        runs.append(
            {
                "key": f"{provider}/{model}/{run_date}",
                "provider": provider,
                "model": model,
                "date": run_date,
                "values": _metric_values(report),
            }
        )
    runs.sort(key=lambda item: item["key"])
    return {
        "schema_version": 1,
        "metrics": list(CONTROLLED_METRICS),
        "runs": runs,
    }


def _case_expectations(
    report: dict[str, Any],
) -> dict[str, tuple[tuple[str, ...], tuple[str, ...]]]:
    cases = report.get("cases")
    if not isinstance(cases, list):
        raise ValueError("quality report is missing cases")
    expectations: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}
    for case in cases:
        if not isinstance(case, dict) or "case_id" not in case:
            raise ValueError("quality report contains an invalid case")
        case_id = str(case["case_id"])
        if case_id in expectations:
            raise ValueError(f"quality report contains duplicate case: {case_id}")
        bindings = case.get("expected_bindings")
        chart_types = case.get("expected_chart_types")
        if not isinstance(bindings, list) or not isinstance(chart_types, list):
            raise ValueError(f"quality report case {case_id} is missing expectations")
        expectations[case_id] = (
            tuple(str(item) for item in bindings),
            tuple(str(item) for item in chart_types),
        )
    return expectations


def _comparability_issues(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> list[str]:
    issues: list[str] = []
    baseline_schema = baseline.get("schema_version")
    candidate_schema = candidate.get("schema_version")
    if baseline_schema != candidate_schema:
        issues.append(f"schema_version mismatch: {baseline_schema} != {candidate_schema}")
    elif baseline_schema != SUPPORTED_SCHEMA_VERSION:
        issues.append(f"unsupported baseline schema_version: {baseline_schema}")
        issues.append(f"unsupported candidate schema_version: {candidate_schema}")
    baseline_run = baseline.get("run")
    candidate_run = candidate.get("run")
    if not isinstance(baseline_run, dict) or not isinstance(candidate_run, dict):
        raise ValueError("quality report is missing run metadata")
    baseline_fixture = baseline_run.get("fixture")
    candidate_fixture = candidate_run.get("fixture")
    if baseline_fixture != candidate_fixture:
        issues.append(f"fixture mismatch: {baseline_fixture} != {candidate_fixture}")
    elif not (isinstance(baseline_fixture, str) and baseline_fixture):
        issues.append(f"unsupported baseline fixture: {baseline_fixture}")
        issues.append(f"unsupported candidate fixture: {candidate_fixture}")
    baseline_cases = _case_expectations(baseline)
    candidate_cases = _case_expectations(candidate)
    baseline_ids = sorted(baseline_cases)
    candidate_ids = sorted(candidate_cases)
    if baseline_ids != candidate_ids:
        issues.append(f"case ids mismatch: {baseline_ids} != {candidate_ids}")
        return issues
    for case_id in baseline_ids:
        baseline_bindings, baseline_charts = baseline_cases[case_id]
        candidate_bindings, candidate_charts = candidate_cases[case_id]
        if baseline_bindings != candidate_bindings:
            issues.append(f"case {case_id} expected_bindings mismatch")
        if baseline_charts != candidate_charts:
            issues.append(f"case {case_id} expected_chart_types mismatch")
    return issues


def evaluate_upgrade(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    baseline_provider, baseline_model, baseline_date = _report_identity(baseline)
    candidate_provider, candidate_model, candidate_date = _report_identity(candidate)
    baseline_values = _metric_values(baseline)
    candidate_values = _metric_values(candidate)
    incompatibilities = _comparability_issues(baseline, candidate)
    regressions = []
    for metric in CONTROLLED_METRICS:
        direction = "higher_is_better" if metric in HIGHER_IS_BETTER else "lower_is_better"
        baseline_value = baseline_values[metric]
        candidate_value = candidate_values[metric]
        regressed = (
            candidate_value < baseline_value
            if metric in HIGHER_IS_BETTER
            else candidate_value > baseline_value
        )
        if regressed:
            regressions.append(
                {
                    "metric": metric,
                    "baseline": baseline_value,
                    "candidate": candidate_value,
                    "direction": direction,
                }
            )
    return {
        "schema_version": 1,
        "allowed": not regressions and not incompatibilities,
        "baseline_model": baseline_model,
        "candidate_model": candidate_model,
        "baseline": {
            "provider": baseline_provider,
            "date": baseline_date,
            "values": baseline_values,
        },
        "candidate": {
            "provider": candidate_provider,
            "date": candidate_date,
            "values": candidate_values,
        },
        "incompatibilities": incompatibilities,
        "regressions": regressions,
    }


def build_trend(reports: list[dict[str, Any]]) -> dict[str, Any]:
    if not reports:
        raise ValueError("trend requires at least one quality report")
    points = []
    for report in reports:
        provider, model, run_date = _report_identity(report)
        points.append(
            {
                "date": run_date,
                "provider": provider,
                "model": model,
                "values": _metric_values(report),
            }
        )
    points.sort(key=lambda point: (point["date"], point["provider"], point["model"]))
    return {
        "schema_version": 1,
        "metrics": list(CONTROLLED_METRICS),
        "points": points,
    }


def _format_metric(metric: str, value: int | float) -> str:
    if metric.endswith("_rate") or metric.endswith("_accuracy"):
        return f"{float(value) * 100:.2f}%"
    if metric == "cost_usd":
        return f"${float(value):.6f}"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def render_dashboard(trend: dict[str, Any]) -> str:
    points = trend.get("points")
    if not isinstance(points, list):
        raise ValueError("trend is missing points")
    headings = "".join(
        f"<th>{html.escape(_METRIC_LABELS[name])}</th>" for name in CONTROLLED_METRICS
    )
    rows = []
    for point in points:
        values = point["values"]
        cells = "".join(
            f"<td>{html.escape(_format_metric(metric, values[metric]))}</td>"
            for metric in CONTROLLED_METRICS
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(point['date']))}</td>"
            f"<td>{html.escape(str(point['provider']))}</td>"
            f"<td>{html.escape(str(point['model']))}</td>"
            f"{cells}</tr>"
        )
    return (
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>DataPulse 质量趋势</title><style>"
        "body{font-family:system-ui,sans-serif;margin:24px;color:#18212b;background:#f7f8fa}"
        "h1{font-size:24px;letter-spacing:0}table{width:100%;border-collapse:collapse;background:#fff}"
        "th,td{padding:10px;border:1px solid #d8dde3;text-align:right;white-space:nowrap}"
        "th:nth-child(-n+3),td:nth-child(-n+3){text-align:left}"
        "thead{background:#edf1f4}</style></head><body><h1>DataPulse 质量趋势</h1>"
        f"<table><thead><tr><th>日期</th><th>Provider</th><th>模型</th>{headings}</tr>"
        f"</thead><tbody>{''.join(rows)}</tbody></table></body></html>"
    )


def write_dashboard(trend: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_dashboard(trend), encoding="utf-8")


def _sample_id(provider: str, model: str, case_id: str) -> str:
    value = f"{provider}-{model}-{case_id}".lower()
    return re.sub(r"[^a-z0-9._-]+", "-", value).strip("-")


def build_failure_samples(reports: list[dict[str, Any]]) -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    fixture_versions: set[str] = set()
    for report in reports:
        provider, model, run_date = _report_identity(report)
        run = report["run"]
        fixture_versions.add(str(run.get("fixture", "")))
        cases = report.get("cases")
        if not isinstance(cases, list):
            raise ValueError("quality report is missing cases")
        for case in cases:
            expected_bindings = list(case.get("expected_bindings", []))
            actual_bindings = dict(case.get("actual_bindings", {}))
            expected_chart_types = list(case.get("expected_chart_types", []))
            actual_chart_type = case.get("actual_chart_type")
            reasons = []
            if not case.get("success", False):
                reasons.append("generation_failed")
            if any(actual_bindings.get(field) != field for field in expected_bindings):
                reasons.append("binding_mismatch")
            if actual_chart_type not in expected_chart_types:
                reasons.append("chart_type_mismatch")
            if not case.get("draft_produced", False):
                reasons.append("draft_missing")
            if not reasons:
                continue
            case_id = str(case["case_id"])
            samples.append(
                {
                    "sample_id": _sample_id(provider, model, case_id),
                    "source": {"provider": provider, "model": model, "date": run_date},
                    "case_id": case_id,
                    "scenario": str(case.get("scenario", "")),
                    "expected_bindings": expected_bindings,
                    "expected_chart_types": expected_chart_types,
                    "actual_bindings": actual_bindings,
                    "actual_chart_type": actual_chart_type,
                    "error_code": case.get("error_code"),
                    "draft_produced": bool(case.get("draft_produced", False)),
                    "failure_reasons": reasons,
                }
            )
    samples.sort(key=lambda sample: sample["sample_id"])
    if len(fixture_versions) != 1:
        raise ValueError("failure samples require reports from one fixture version")
    return {
        "schema_version": 1,
        "fixture_version": next(iter(fixture_versions)),
        "samples": samples,
    }
