"""Benchmark runner entry point (Phase 1.5)."""

from __future__ import annotations

from pathlib import Path

import typer

from repopilot.eval import write_eval_compare, write_eval_summary
from repopilot.eval.loader import load_run_record, resolve_task_run_dir
from repopilot.eval.visualize import open_run_view, write_run_view
from repopilot.runner.adhoc_run import run_adhoc_task
from repopilot.runner.run_task import find_project_root, resolve_task_dir, run_benchmark_task
from repopilot.trace import TraceContext, record_trace

app = typer.Typer(help="Run RepoPilot benchmark tasks.")
eval_app = typer.Typer(help="Aggregate and report on benchmark runs.")
adhoc_app = typer.Typer(help="Run adhoc user-reported bugs without a benchmarks/ task directory.")
app.add_typer(eval_app, name="eval")
app.add_typer(adhoc_app, name="adhoc")


@app.command("run")
def run(
    task: Path | None = typer.Argument(
        None,
        help="Task directory or task_id under benchmarks/ (omit when using --adhoc)",
    ),
    project_root: Path | None = typer.Option(
        None,
        "--project-root",
        help="Repository root (default: git toplevel from cwd)",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print planned commands without running"),
    skip_mini: bool = typer.Option(
        False,
        "--skip-mini",
        help="Prepare workspace and verify only; skip mini agent",
    ),
    no_restore: bool = typer.Option(
        False,
        "--no-restore",
        help="Keep the task git worktree after run (default: remove runs/{task_id}/.workspace)",
    ),
    adhoc_repo: str | None = typer.Option(
        None,
        "--adhoc",
        help="Local repo path or git URL for an ephemeral adhoc run (requires --issue and --test-cmd)",
    ),
    issue: Path | None = typer.Option(
        None,
        "--issue",
        "-i",
        help="Issue markdown file (required with --adhoc)",
    ),
    test_cmd: str | None = typer.Option(
        None,
        "--test-cmd",
        help="Runner verify command (required with --adhoc)",
    ),
    commit: str | None = typer.Option(
        None,
        "--commit",
        help="Git ref for --adhoc repo snapshot (default: HEAD)",
    ),
    verify_tier: str = typer.Option(
        "strict",
        "--verify-tier",
        help="strict | smoke — recorded in trace task_tags",
    ),
    tests_tag: str = typer.Option(
        "tests_preexisting",
        "--tests-tag",
        help="tests_preexisting | tests_generated",
    ),
) -> None:
    """Run a benchmark task end-to-end, or an adhoc repo + issue with --adhoc."""
    root = (project_root or find_project_root()).resolve()

    if adhoc_repo:
        if issue is None or test_cmd is None:
            raise typer.BadParameter("--issue and --test-cmd are required with --adhoc")
        result = run_adhoc_task(
            adhoc_repo,
            issue,
            test_command=test_cmd,
            project_root=root,
            commit=commit,
            verify_tier=verify_tier,
            tests_tag=tests_tag,
            skip_mini=skip_mini,
            restore_workspace=not no_restore,
            dry_run=dry_run,
        )
    else:
        if task is None:
            raise typer.BadParameter("Provide a benchmark task id/path, or use --adhoc with --issue and --test-cmd")
        task_dir = resolve_task_dir(task, benchmarks_root=root / "benchmarks")
        result = run_benchmark_task(
            task_dir,
            project_root=root,
            skip_mini=skip_mini,
            restore_workspace=not no_restore,
            dry_run=dry_run,
        )

    if dry_run:
        return
    typer.echo(f"Task {result.task_id} finished.")
    typer.echo(f"  mini exit code: {result.mini_exit_code}")
    typer.echo(f"  verify exit code: {result.test_exit_code} ({'passed' if result.tests_passed else 'failed'})")
    typer.echo(f"  artifacts: {result.output_dir}/")


@adhoc_app.command("run")
def adhoc_run(
    repo: str = typer.Argument(..., help="Local repo path or git URL"),
    issue: Path = typer.Argument(..., help="Issue markdown file"),
    test_cmd: str = typer.Option(..., "--test-cmd", help="Runner verify command"),
    project_root: Path | None = typer.Option(None, "--project-root"),
    commit: str | None = typer.Option(None, "--commit", help="Git ref (default: HEAD)"),
    verify_tier: str = typer.Option("strict", "--verify-tier"),
    tests_tag: str = typer.Option("tests_preexisting", "--tests-tag"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    skip_mini: bool = typer.Option(False, "--skip-mini"),
    no_restore: bool = typer.Option(False, "--no-restore"),
) -> None:
    """Run an adhoc task; outputs go to runs/adhoc/{task_id}/."""
    root = (project_root or find_project_root()).resolve()
    result = run_adhoc_task(
        repo,
        issue,
        test_command=test_cmd,
        project_root=root,
        commit=commit,
        verify_tier=verify_tier,
        tests_tag=tests_tag,
        skip_mini=skip_mini,
        restore_workspace=not no_restore,
        dry_run=dry_run,
    )
    if dry_run:
        return
    typer.echo(f"Task {result.task_id} finished.")
    typer.echo(f"  mini exit code: {result.mini_exit_code}")
    typer.echo(f"  verify exit code: {result.test_exit_code} ({'passed' if result.tests_passed else 'failed'})")
    typer.echo(f"  artifacts: {result.output_dir}/")


@app.command("trace")
def trace(
    trajectory: Path = typer.Argument(..., help="Path to trajectory.traj.json"),
    output_dir: Path | None = typer.Option(
        None,
        "-o",
        "--output-dir",
        help="Output directory (default: same directory as trajectory)",
    ),
    task_id: str | None = typer.Option(None, "--task-id", help="Task id for the trace record"),
) -> None:
    """Build trace.json / patch.diff / test.log / final_report.md / failure_reason.md from a trajectory."""
    trajectory = trajectory.resolve()
    if not trajectory.is_file():
        raise typer.BadParameter(f"Trajectory not found: {trajectory}")
    out = (output_dir or trajectory.parent).resolve()
    artifacts = record_trace(
        trajectory,
        out,
        ctx=TraceContext(task_id=task_id or out.name),
    )
    typer.echo(f"Wrote trace artifacts to {out}/")
    typer.echo(f"  {artifacts.trace_json.name}")
    typer.echo(f"  {artifacts.patch_diff.name}")
    typer.echo(f"  {artifacts.test_log.name}")
    typer.echo(f"  {artifacts.final_report.name}")
    typer.echo(f"  {artifacts.failure_reason.name}")


@eval_app.command("summary")
def eval_summary(
    runs_dir: Path = typer.Option(
        Path("runs"),
        "--runs-dir",
        help="Directory containing per-task run outputs",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "-o",
        "--output-dir",
        help="Eval output directory (default: runs/eval/summary)",
    ),
    benchmark_only: bool = typer.Option(
        True,
        "--benchmark-only/--include-adhoc",
        help="Exclude adhoc runs from benchmark aggregate (default). Use --include-adhoc to merge all runs.",
    ),
    adhoc_only: bool = typer.Option(
        False,
        "--adhoc-only",
        help="Summarize adhoc runs only (separate bucket)",
    ),
) -> None:
    """Aggregate trace.json + run_meta.yaml into eval reports."""
    root = find_project_root().resolve()
    runs = (runs_dir if runs_dir.is_absolute() else root / runs_dir).resolve()
    out = write_eval_summary(
        runs,
        output_dir=output_dir,
        benchmark_only=benchmark_only and not adhoc_only,
        adhoc_only=adhoc_only,
        include_adhoc=not benchmark_only and not adhoc_only,
    )
    typer.echo(f"Wrote eval summary to {out}/")
    typer.echo("  eval_report.md")
    typer.echo("  metrics.json")
    typer.echo("  failure_breakdown.md")
    typer.echo("  comparison_table.csv")
    typer.echo(f"  {runs / 'eval' / 'compare' / 'comparison_report.md'}")
    typer.echo("  ../eval/{task_id}/trajectory_analysis.md (per task)")
    typer.echo("  ../eval/{task_id}/view.html (per task)")


@eval_app.command("compare")
def eval_compare(
    task: str | None = typer.Option(None, "--task", help="Filter to a single task_id"),
    runs_dir: Path = typer.Option(
        Path("runs"),
        "--runs-dir",
        help="Directory containing per-task run outputs",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "-o",
        "--output-dir",
        help="Output directory (default: runs/eval/compare)",
    ),
    benchmark_only: bool = typer.Option(
        True,
        "--benchmark-only/--include-adhoc",
        help="Exclude adhoc runs from comparison (default)",
    ),
    adhoc_only: bool = typer.Option(False, "--adhoc-only", help="Compare adhoc runs only"),
) -> None:
    """Compare tasks on steps, cost, and files touched."""
    root = find_project_root().resolve()
    runs = (runs_dir if runs_dir.is_absolute() else root / runs_dir).resolve()
    out = write_eval_compare(
        runs,
        task_id=task,
        output_dir=output_dir,
        benchmark_only=benchmark_only and not adhoc_only,
        adhoc_only=adhoc_only,
        include_adhoc=not benchmark_only and not adhoc_only,
    )
    typer.echo(f"Wrote comparison to {out}/")
    typer.echo("  comparison_report.md")
    typer.echo("  comparison_table.csv")


@eval_app.command("breakdown")
def eval_breakdown(
    by: str | None = typer.Option(
        None,
        "--by",
        help="Group by: failure_mode, difficulty, failure_category, failure_stage",
    ),
    runs_dir: Path = typer.Option(
        Path("runs"),
        "--runs-dir",
        help="Directory containing per-task run outputs",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "-o",
        "--output-dir",
        help="Output directory (default: runs/eval/summary)",
    ),
    benchmark_only: bool = typer.Option(
        True,
        "--benchmark-only/--include-adhoc",
        help="Benchmark failure breakdown only (default). Adhoc section appended when present.",
    ),
    adhoc_only: bool = typer.Option(False, "--adhoc-only", help="Adhoc breakdown only"),
) -> None:
    """Regenerate failure breakdown with failure_mode / difficulty tags."""
    root = find_project_root().resolve()
    runs = (runs_dir if runs_dir.is_absolute() else root / runs_dir).resolve()
    out_dir = (output_dir or runs / "eval" / "summary").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    from repopilot.eval.adhoc import partition_runs
    from repopilot.eval.failure_analysis import BY_FIELDS, adhoc_tag_breakdown, render_adhoc_breakdown_section, render_tag_breakdown, tag_breakdown
    from repopilot.eval.loader import load_all_runs

    if by and by not in BY_FIELDS:
        allowed = ", ".join(sorted(BY_FIELDS))
        raise typer.BadParameter(f"Unknown --by {by!r}; choose from: {allowed}")

    all_records = load_all_runs(runs)
    if not all_records:
        raise typer.BadParameter(f"No runs with trace.json found under {runs}")
    benchmark_records, adhoc_records = partition_runs(all_records)

    if adhoc_only:
        records = adhoc_records
        md = render_adhoc_breakdown_section(adhoc_tag_breakdown(records))
    elif benchmark_only:
        records = benchmark_records
        md = render_tag_breakdown(tag_breakdown(records), by=by)
        if adhoc_records:
            md = md.rstrip() + "\n\n" + render_adhoc_breakdown_section(adhoc_tag_breakdown(adhoc_records))
    else:
        records = all_records
        md = render_tag_breakdown(tag_breakdown(records), by=by)

    if not records and not adhoc_records:
        raise typer.BadParameter(f"No runs in selected scope under {runs}")
    (out_dir / "failure_breakdown.md").write_text(md)
    typer.echo(f"Wrote {out_dir / 'failure_breakdown.md'}")


@eval_app.command("view")
def eval_view(
    run: Path = typer.Argument(..., help="Task id (e.g. task_001_sudoku) or path to run directory"),
    runs_dir: Path = typer.Option(
        Path("runs"),
        "--runs-dir",
        help="Runs root when passing a task id",
    ),
    output: Path | None = typer.Option(
        None,
        "-o",
        "--output",
        help="HTML output path (default: runs/eval/{task_id}/view.html)",
    ),
    open_browser: bool = typer.Option(False, "--open", help="Open the report in your default browser"),
) -> None:
    """Render an HTML trajectory view for one run."""
    root = find_project_root().resolve()
    runs = (runs_dir if runs_dir.is_absolute() else root / runs_dir).resolve()

    run_path = run if run.is_absolute() else (root / run).resolve()
    if run_path.is_dir() and (run_path / "trace.json").is_file():
        run_dir = run_path
    else:
        task_id = run.name if run.name else str(run)
        resolved = resolve_task_run_dir(runs, task_id)
        if resolved is None:
            raise typer.BadParameter(f"No run found for {run!r} under {runs}")
        run_dir = resolved

    record = load_run_record(run_dir)
    out = write_run_view(record, output)
    typer.echo(f"Wrote {out}")
    if open_browser:
        open_run_view(out)
        typer.echo("Opened in browser.")


if __name__ == "__main__":
    app()
