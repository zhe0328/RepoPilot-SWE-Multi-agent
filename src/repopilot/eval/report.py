"""Render evaluation reports from aggregated metrics."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from repopilot.eval.adhoc import partition_runs
from repopilot.eval.compare import DEFAULT_PAIRS, comparison_rows, render_comparison_report, write_comparison_csv
from repopilot.eval.failure_analysis import (
    adhoc_tag_breakdown,
    render_adhoc_breakdown_section,
    render_tag_breakdown,
    tag_breakdown,
)
from repopilot.eval.loader import RunRecord, load_all_runs, load_task_runs
from repopilot.eval.metrics import aggregate_runs, run_records_table
from repopilot.eval.trajectory_analysis import render_trajectory_analysis
from repopilot.eval.visualize import render_failure_distribution_charts, write_run_view


def _render_eval_report(
    records: list[RunRecord],
    metrics: dict,
    breakdown: dict,
    runs_dir: Path,
    *,
    scope: str = "benchmark",
    adhoc_metrics: dict | None = None,
    adhoc_records: list[RunRecord] | None = None,
) -> str:
    scope_label = {
        "benchmark": "benchmark tasks only (`task_*`)",
        "adhoc": "adhoc tasks only (`adhoc_*`)",
        "all": "benchmark + adhoc",
    }.get(scope, scope)

    lines = [
        "# RepoPilot Evaluation Summary",
        "",
        f"- **Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"- **Runs directory:** `{runs_dir}`",
        f"- **Scope:** {scope_label}",
        f"- **Total runs (in scope):** {metrics['total_runs']}",
        "",
        "## Aggregate metrics",
        "",
        f"- **Success rate (outcome):** {metrics['success_count']}/{metrics['total_runs']} ({metrics['success_rate']}%)",
        f"- **Verify pass rate (runner):** {metrics['verify_pass_count']}/{metrics['total_runs']} ({metrics['verify_pass_rate']}%)",
        f"- **Avg cost:** ${metrics['avg_cost']:.4f}",
        f"- **Avg steps:** {metrics['avg_steps']}",
        f"- **Avg API calls:** {metrics['avg_api_calls']}",
        f"- **Avg repair rounds:** {metrics['avg_repair_rounds']}",
        "",
    ]

    if metrics.get("by_agent_mode"):
        lines.extend(
            [
                "## By agent mode",
                "",
                "| Mode | Runs | Success | Verify pass | Avg cost | Avg steps |",
                "|------|-----:|--------:|------------:|---------:|----------:|",
            ]
        )
        for mode, stats in metrics["by_agent_mode"].items():
            lines.append(
                f"| {mode} | {stats['runs']} | {stats['success_rate']}% | {stats['verify_pass_rate']}% | "
                f"${stats['avg_cost']:.4f} | {stats['avg_steps']} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Run table",
            "",
            "| task_id | mode | outcome | verify | failure | stage | step | cost |",
            "|---------|------|---------|--------|---------|-------|-----:|-----:|",
        ]
    )
    for row in run_records_table(records):
        verify = "yes" if row["tests_passed"] is True else "no" if row["tests_passed"] is False else "?"
        lines.append(
            f"| {row['task_id']} | {row['agent_mode']} | {row['outcome']} | {verify} | "
            f"{row['failure_category'] or '—'} | {row['failure_stage'] or '—'} | {row['failed_step'] or '—'} | "
            f"${row['cost']:.4f} |"
        )
    lines.append("")

    if breakdown["failed_runs"]:
        chart_section = render_failure_distribution_charts(breakdown)
        if chart_section:
            lines.extend([chart_section])
        lines.extend(["## Failure breakdown", ""])
        lines.append("### By category")
        lines.append("")
        for cat, count in breakdown["by_category"].items():
            lines.append(f"- `{cat}`: {count}")
        lines.extend(["", "### By stage", ""])
        for stage, count in breakdown["by_stage"].items():
            lines.append(f"- `{stage}`: {count}")
        lines.append("")

    if breakdown.get("by_failure_mode"):
        lines.extend(["## By task tag (failure_mode)", ""])
        for mode, count in breakdown["by_failure_mode"].items():
            outcomes = breakdown.get("outcome_by_failure_mode", {}).get(mode, {})
            lines.append(
                f"- `{mode}`: {count} — {outcomes.get('success', 0)} success, {outcomes.get('failure', 0)} failure"
            )
        lines.append("")

    if adhoc_metrics and adhoc_records is not None:
        lines.extend(
            [
                "## Adhoc runs (separate bucket — excluded from benchmark metrics above)",
                "",
                f"- **Adhoc runs:** {adhoc_metrics['total_runs']}",
                f"- **Success rate:** {adhoc_metrics['success_count']}/{adhoc_metrics['total_runs']} "
                f"({adhoc_metrics['success_rate']}%)",
                f"- **Verify pass rate:** {adhoc_metrics['verify_pass_count']}/{adhoc_metrics['total_runs']} "
                f"({adhoc_metrics['verify_pass_rate']}%)",
                f"- **Avg cost:** ${adhoc_metrics['avg_cost']:.4f}",
                "",
                "| task_id | mode | outcome | verify | cost |",
                "|---------|------|---------|--------|-----:|",
            ]
        )
        for row in run_records_table(adhoc_records):
            verify = "yes" if row["tests_passed"] is True else "no" if row["tests_passed"] is False else "?"
            lines.append(
                f"| {row['task_id']} | {row['agent_mode']} | {row['outcome']} | {verify} | ${row['cost']:.4f} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Artifacts",
            "",
            "| File | Description |",
            "|------|-------------|",
            "| `eval_report.md` | This summary |",
            "| `metrics.json` | Machine-readable aggregate |",
            "| `failure_breakdown.md` | Failure taxonomy + tag breakdown |",
            "| `comparison_table.csv` | Cross-task metrics |",
            "| `../compare/comparison_report.md` | Detailed comparison |",
            "| `{task_id}/run_summary.md` | Per-task drill-down |",
            "| `{task_id}/trajectory_analysis.md` | Steps / files touched |",
            "| `{task_id}/view.html` | Interactive HTML run view |",
            "",
        ]
    )
    return "\n".join(lines)


def _render_task_summary(record: RunRecord) -> str:
    lines = [
        f"# Run Summary — {record.task_id}",
        "",
        f"- **Agent mode:** {record.agent_mode}",
        f"- **Model:** {record.model}",
        f"- **Outcome:** {record.outcome}",
        f"- **Runner verify passed:** {record.tests_passed}",
        f"- **Base commit:** `{record.base_commit or 'unknown'}`",
        f"- **Cost:** ${record.instance_cost:.4f} ({record.api_calls} API calls)",
        f"- **Steps:** {record.step_count}",
        "",
    ]

    if record.outcome != "success":
        lines.extend(
            [
                "## Failure attribution",
                "",
                f"- **Category:** `{record.failure_category}`",
                f"- **Stage:** `{record.failure_stage}`",
                f"- **Failed step:** {record.failed_step}",
                f"- **Message:** {record.failure_message}",
                "",
            ]
        )

    if record.pytest_runs:
        lines.extend(["## Pytest runs", ""])
        for run in record.pytest_runs:
            rc = run.get("returncode")
            lines.append(f"- **{run.get('phase')}:** exit {rc} {'✅' if rc == 0 else '❌'}")
        lines.append("")

    if record.steps:
        lines.extend(["## Step timeline", ""])
        for step in record.steps:
            lines.append(f"### Step {step.get('step')}")
            if step.get("reasoning"):
                lines.append(step["reasoning"][:300] + ("…" if len(step["reasoning"]) > 300 else ""))
                lines.append("")
            for i, tc in enumerate(step.get("tool_calls", []), 1):
                preview = tc.get("command", "").replace("\n", " ")[:100]
                lines.append(f"{i}. `[{tc.get('returncode')}]` `{preview}{'…' if len(tc.get('command','')) > 100 else ''}`")
            lines.append("")

    lines.extend(
        [
            "## Source artifacts",
            "",
            f"- Trace: `{record.trace_path}`",
            f"- Meta: `{record.meta_path or 'n/a'}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_eval_summary(
    runs_dir: Path,
    output_dir: Path | None = None,
    *,
    benchmark_only: bool = True,
    adhoc_only: bool = False,
    include_adhoc: bool = False,
) -> Path:
    runs_dir = runs_dir.resolve()
    output_dir = (output_dir or runs_dir / "eval" / "summary").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    all_records = load_all_runs(runs_dir)
    if not all_records:
        raise FileNotFoundError(f"No runs with trace.json found under {runs_dir}")

    benchmark_records, adhoc_records = partition_runs(all_records)

    if adhoc_only:
        records = adhoc_records
        scope = "adhoc"
    elif include_adhoc:
        records = all_records
        scope = "all"
    else:
        records = benchmark_records
        scope = "benchmark"

    if not records:
        label = "adhoc" if adhoc_only else "benchmark"
        raise FileNotFoundError(f"No {label} runs with trace.json found under {runs_dir}")

    metrics = aggregate_runs(records)
    breakdown = tag_breakdown(records)
    rows = comparison_rows(records)

    adhoc_metrics = aggregate_runs(adhoc_records) if adhoc_records and scope == "benchmark" else None
    adhoc_breakdown = adhoc_tag_breakdown(adhoc_records) if adhoc_records and scope == "benchmark" else None

    failure_md = render_tag_breakdown(breakdown)
    if adhoc_breakdown and adhoc_records:
        failure_md = failure_md.rstrip() + "\n\n" + render_adhoc_breakdown_section(adhoc_breakdown)

    (output_dir / "eval_report.md").write_text(
        _render_eval_report(
            records,
            metrics,
            breakdown,
            runs_dir,
            scope=scope,
            adhoc_metrics=adhoc_metrics,
            adhoc_records=adhoc_records if scope == "benchmark" else None,
        )
    )
    (output_dir / "metrics.json").write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "runs_dir": str(runs_dir),
                "scope": scope,
                "metrics": metrics,
                "adhoc_metrics": adhoc_metrics,
                "runs": run_records_table(records),
                "adhoc_runs": run_records_table(adhoc_records) if adhoc_records else [],
                "comparison": rows,
                "breakdown": {k: v for k, v in breakdown.items() if k != "examples"},
                "adhoc_breakdown": (
                    {k: v for k, v in adhoc_breakdown.items() if k != "examples"} if adhoc_breakdown else None
                ),
            },
            indent=2,
        )
        + "\n"
    )
    (output_dir / "failure_breakdown.md").write_text(failure_md)
    write_comparison_csv(rows, output_dir / "comparison_table.csv")

    compare_dir = runs_dir / "eval" / "compare"
    compare_dir.mkdir(parents=True, exist_ok=True)
    (compare_dir / "comparison_report.md").write_text(
        render_comparison_report(records, highlight_pairs=DEFAULT_PAIRS)
    )

    task_eval_root = runs_dir / "eval"
    for record in records:
        task_out = task_eval_root / record.task_id
        task_out.mkdir(parents=True, exist_ok=True)
        (task_out / "run_summary.md").write_text(_render_task_summary(record))
        (task_out / "trajectory_analysis.md").write_text(render_trajectory_analysis(record))
        write_run_view(record, task_out / "view.html")

    return output_dir


def write_eval_summary_legacy(
    runs_dir: Path,
    output_dir: Path | None = None,
) -> Path:
    """All runs in one aggregate (legacy include-adhoc behavior)."""
    return write_eval_summary(runs_dir, output_dir, include_adhoc=True)


def write_eval_compare(
    runs_dir: Path,
    *,
    task_id: str | None = None,
    output_dir: Path | None = None,
    benchmark_only: bool = True,
    adhoc_only: bool = False,
    include_adhoc: bool = False,
) -> Path:
    runs_dir = runs_dir.resolve()
    output_dir = (output_dir or runs_dir / "eval" / "compare").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    all_records = load_all_runs(runs_dir)
    if not all_records:
        raise FileNotFoundError(f"No runs with trace.json found under {runs_dir}")

    benchmark_records, adhoc_records = partition_runs(all_records)
    if adhoc_only:
        records = adhoc_records
    elif include_adhoc:
        records = all_records
    else:
        records = benchmark_records

    if not records:
        raise FileNotFoundError(f"No runs in selected scope under {runs_dir}")

    if task_id:
        task_records = load_task_runs(runs_dir, task_id)
        if not task_records:
            raise FileNotFoundError(f"No runs found for task {task_id!r} under {runs_dir}")
        report = render_comparison_report(task_records, task_filter=task_id, runs_dir=runs_dir)
        rows = comparison_rows(task_records)
    else:
        report = render_comparison_report(records, highlight_pairs=DEFAULT_PAIRS, runs_dir=runs_dir)
        rows = comparison_rows(records)

    (output_dir / "comparison_report.md").write_text(report)
    write_comparison_csv(rows, output_dir / "comparison_table.csv")
    return output_dir
