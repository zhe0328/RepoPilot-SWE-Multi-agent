"""Ephemeral adhoc task runs without a benchmarks/ directory (Adhoc Phase C)."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml

from repopilot.runner.repo_resolve import resolve_git_ref, resolve_repository
from repopilot.runner.run_task import find_project_root, run_benchmark_task
from repopilot.schema import TaskConfig, load_task_config


def make_adhoc_task_id(repo_spec: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tail = repo_spec.rstrip("/").split("/")[-1].replace(".git", "")
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in tail)[:24] or "repo"
    return f"adhoc_{safe}_{ts}"


def _tests_authored_tag(tests_tag: str) -> str:
    if tests_tag in ("tests_preexisting", "tests_generated"):
        return tests_tag
    raise ValueError(f"tests_tag must be tests_preexisting or tests_generated, got {tests_tag!r}")


def write_adhoc_task_dir(
    task_dir: Path,
    *,
    task_id: str,
    repo_path: Path,
    base_commit: str,
    issue_path: Path,
    test_command: str,
    verify_tier: str | None = "strict",
    tests_tag: str = "tests_preexisting",
) -> None:
    _tests_authored_tag(tests_tag)
    task_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(issue_path, task_dir / "issue.md")
    payload = {
        "task_id": task_id,
        "description": f"Adhoc run for {repo_path.name}",
        "repo": {
            "path": str(repo_path),
            "base_commit": base_commit,
        },
        "issue_file": "issue.md",
        "test_command": test_command,
        "expected_behavior": "Runner verify passes after agent fix",
        "eval": {
            "failure_mode": "adhoc",
            "difficulty": "user_reported",
            "verify_tier": verify_tier,
            "tags": ["adhoc", tests_tag],
        },
        "agent": {
            "mode": "baseline",
            "mini_flags": ["-y", "--exit-immediately", "--cost-limit", "0.50"],
            "output_trajectory": "trajectory.traj.json",
        },
    }
    (task_dir / "config.yaml").write_text(yaml.safe_dump(payload, sort_keys=False))


def build_adhoc_task_config(
    task_dir: Path,
    *,
    repo_path: Path,
    base_commit: str,
    issue_path: Path,
    test_command: str,
    task_id: str,
    verify_tier: str | None = "strict",
    tests_tag: str = "tests_preexisting",
) -> TaskConfig:
    write_adhoc_task_dir(
        task_dir,
        task_id=task_id,
        repo_path=repo_path,
        base_commit=base_commit,
        issue_path=issue_path,
        test_command=test_command,
        verify_tier=verify_tier,
        tests_tag=tests_tag,
    )
    return load_task_config(
        yaml.safe_load((task_dir / "config.yaml").read_text()),
        task_dir=task_dir,
    )


def run_adhoc_task(
    repo_spec: str,
    issue_path: Path,
    *,
    test_command: str,
    project_root: Path | None = None,
    commit: str | None = None,
    verify_tier: str | None = "strict",
    tests_tag: str = "tests_preexisting",
    skip_mini: bool = False,
    restore_workspace: bool = True,
    dry_run: bool = False,
) -> "RunResult":
    from repopilot.runner.run_task import RunResult

    root = (project_root or find_project_root()).resolve()
    issue_path = issue_path.expanduser().resolve()
    if not issue_path.is_file():
        raise FileNotFoundError(f"Issue file not found: {issue_path}")

    cache_root = root / "runs" / ".cache" / "repos"
    repo_path = resolve_repository(repo_spec, cache_root=cache_root)
    base_commit = resolve_git_ref(repo_path, commit)

    task_id = make_adhoc_task_id(repo_spec)
    output_dir = (root / "runs" / "adhoc" / task_id).resolve()
    task_dir = output_dir

    build_adhoc_task_config(
        task_dir,
        task_id=task_id,
        repo_path=repo_path,
        base_commit=base_commit,
        issue_path=issue_path,
        test_command=test_command,
        verify_tier=verify_tier,
        tests_tag=tests_tag,
    )

    return run_benchmark_task(
        task_dir,
        project_root=root,
        skip_mini=skip_mini,
        restore_workspace=restore_workspace,
        dry_run=dry_run,
        output_dir=output_dir,
    )
