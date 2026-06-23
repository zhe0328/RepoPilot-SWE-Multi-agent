"""Benchmark task orchestration (Phase 1.5)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from repopilot.schema import TaskConfig, load_task
from repopilot.trace import TraceContext, record_trace


@dataclass
class RunResult:
    task_id: str
    base_commit: str
    agent_mode: str
    repo_path: Path
    output_dir: Path
    trajectory_path: Path
    mini_exit_code: int | None
    test_exit_code: int
    tests_passed: bool
    mini_command: list[str]


def find_project_root(start: Path | None = None) -> Path:
    start = (start or Path.cwd()).resolve()
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=start,
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def resolve_task_dir(task_arg: Path, *, benchmarks_root: Path | None = None) -> Path:
    task_arg = task_arg.expanduser()
    if task_arg.is_dir():
        return task_arg.resolve()

    root = find_project_root()
    benchmarks_root = (benchmarks_root or root / "benchmarks").resolve()
    for candidate in (task_arg, benchmarks_root / task_arg, benchmarks_root / task_arg.name):
        if candidate.is_dir():
            return candidate.resolve()
    raise FileNotFoundError(f"Benchmark task directory not found: {task_arg}")


def resolve_repo_path(task: TaskConfig, project_root: Path) -> Path:
    if task.repo.path is not None:
        repo = Path(task.repo.path)
        return repo.resolve() if repo.is_absolute() else (project_root / repo).resolve()
    if task.repo.repo_url is None:
        raise ValueError("repo.path or repo.repo_url must be set")
    raise NotImplementedError("Cloning repo_url is not implemented yet (Phase 1.5 supports repo.path only)")


def build_mini_command(task: TaskConfig, trajectory_path: Path) -> list[str]:
    mini = shutil.which("mini")
    if mini is None:
        raise RuntimeError("mini not found on PATH; install upstream with: pip install -e 'upstream/[dev]'")
    return [
        mini,
        *task.agent.mini_flags,
        "-t",
        task.read_issue(),
        "-o",
        str(trajectory_path),
    ]


def _git_current_ref(repo_path: Path) -> str:
    branch = subprocess.run(
        ["git", "symbolic-ref", "-q", "--short", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if branch.returncode == 0:
        return branch.stdout.strip()
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return sha.stdout.strip()


def _stage_setup_patch(setup_patch: Path | None) -> Path | None:
    """Copy setup patch to a temp file so it survives git checkout."""
    if setup_patch is None:
        return None
    tmp = Path(tempfile.mkstemp(suffix=".patch")[1])
    tmp.write_bytes(setup_patch.read_bytes())
    return tmp


@contextmanager
def prepared_workspace(
    repo_path: Path,
    base_commit: str,
    setup_patch: Path | None,
    *,
    restore: bool = True,
):
    saved_ref = _git_current_ref(repo_path)
    staged_patch = _stage_setup_patch(setup_patch)
    subprocess.run(["git", "checkout", "-f", base_commit], cwd=repo_path, check=True)
    if staged_patch is not None:
        try:
            subprocess.run(["git", "apply", str(staged_patch)], cwd=repo_path, check=True)
        finally:
            staged_patch.unlink(missing_ok=True)
    try:
        yield
    finally:
        if restore:
            subprocess.run(["git", "checkout", "-f", saved_ref], cwd=repo_path, check=True)


def run_verification(task: TaskConfig, repo_path: Path, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        task.test_command,
        shell=True,
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    log_path.write_text(result.stdout + result.stderr)
    return result.returncode


def extract_baseline_artifacts(
    trajectory_path: Path,
    output_dir: Path,
    *,
    issue_path: Path | None = None,
    project_root: Path | None = None,
) -> None:
    root = project_root or find_project_root()
    script = root / "scripts" / "extract_baseline.py"
    if not script.is_file():
        raise FileNotFoundError(f"Missing extraction script: {script}")

    cmd = [sys.executable, str(script), str(trajectory_path), "-o", str(output_dir)]
    if issue_path is not None:
        cmd.extend(["--issue", str(issue_path)])
    subprocess.run(cmd, check=True)


def write_run_meta(result: RunResult, *, started_at: datetime, finished_at: datetime) -> Path:
    meta_path = result.output_dir / "run_meta.yaml"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_id": result.task_id,
        "base_commit": result.base_commit,
        "agent_mode": result.agent_mode,
        "repo_path": str(result.repo_path),
        "output_dir": str(result.output_dir),
        "trajectory": str(result.trajectory_path),
        "mini_command": result.mini_command,
        "mini_exit_code": result.mini_exit_code,
        "test_exit_code": result.test_exit_code,
        "tests_passed": result.tests_passed,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
    }
    meta_path.write_text(yaml.safe_dump(payload, sort_keys=False))
    return meta_path


def run_benchmark_task(
    task_dir: Path,
    *,
    project_root: Path | None = None,
    skip_mini: bool = False,
    restore_workspace: bool = True,
    dry_run: bool = False,
    force_baseline: bool = False,
) -> RunResult:
    started_at = datetime.now(timezone.utc)
    task = load_task(task_dir)
    if force_baseline and task.agent.mode != "baseline":
        raise ValueError(f"Task {task.task_id} is not baseline mode")
    if task.agent.mode == "repopilot":
        raise NotImplementedError("repopilot agent mode is not implemented yet")

    root = (project_root or find_project_root(task_dir)).resolve()
    repo_path = resolve_repo_path(task, root)
    output_dir = (root / "runs" / task.task_id).resolve()
    trajectory_path = (root / task.agent.resolve_output_trajectory(task.task_id)).resolve()
    verify_log = output_dir / "verify_test.log"
    mini_command = build_mini_command(task, trajectory_path)

    if dry_run:
        typer_echo = _get_typer_echo()
        typer_echo(f"task_id: {task.task_id}")
        typer_echo(f"repo_path: {repo_path}")
        typer_echo(f"trajectory: {trajectory_path}")
        typer_echo(f"mini: {' '.join(mini_command)}")
        typer_echo(f"verify: {task.test_command}")
        return RunResult(
            task_id=task.task_id,
            base_commit=task.repo.base_commit,
            agent_mode=task.agent.mode,
            repo_path=repo_path,
            output_dir=output_dir,
            trajectory_path=trajectory_path,
            mini_exit_code=None,
            test_exit_code=0,
            tests_passed=False,
            mini_command=mini_command,
        )

    mini_exit_code: int | None = None
    with prepared_workspace(
        repo_path,
        task.repo.base_commit,
        task.setup_patch_path(),
        restore=restore_workspace,
    ):
        if not skip_mini:
            output_dir.mkdir(parents=True, exist_ok=True)
            mini_result = subprocess.run(mini_command, cwd=repo_path)
            mini_exit_code = mini_result.returncode

        test_exit_code = run_verification(task, repo_path, verify_log)
        tests_passed = test_exit_code == 0

        if trajectory_path.is_file():
            extract_baseline_artifacts(
                trajectory_path,
                output_dir,
                issue_path=task.issue_path(),
                project_root=root,
            )
            record_trace(
                trajectory_path,
                output_dir,
                ctx=TraceContext(
                    task_id=task.task_id,
                    issue_path=str(task.issue_path()),
                    verify_test_log=verify_log if verify_log.is_file() else None,
                    tests_passed=tests_passed,
                    agent_mode=task.agent.mode,
                ),
            )

    finished_at = datetime.now(timezone.utc)
    result = RunResult(
        task_id=task.task_id,
        base_commit=task.repo.base_commit,
        agent_mode=task.agent.mode,
        repo_path=repo_path,
        output_dir=output_dir,
        trajectory_path=trajectory_path,
        mini_exit_code=mini_exit_code,
        test_exit_code=test_exit_code,
        tests_passed=tests_passed,
        mini_command=mini_command,
    )
    write_run_meta(result, started_at=started_at, finished_at=finished_at)
    return result


def _get_typer_echo():
    try:
        import typer

        return typer.echo
    except ImportError:
        return print
