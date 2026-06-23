"""Benchmark runner entry point (Phase 1.5)."""

from __future__ import annotations

from pathlib import Path

import typer

from repopilot.runner.run_task import find_project_root, resolve_task_dir, run_benchmark_task
from repopilot.trace import TraceContext, record_trace

app = typer.Typer(help="Run RepoPilot benchmark tasks.")


@app.command("run")
def run(
    task: Path = typer.Argument(..., help="Task directory or task_id under benchmarks/"),
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
        help="Leave repo on task state after run (do not git checkout back)",
    ),
) -> None:
    """Run a benchmark task end-to-end."""
    root = (project_root or find_project_root()).resolve()
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
    """Build trace.json / patch.diff / test.log / final_report.md from a trajectory."""
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


if __name__ == "__main__":
    app()
