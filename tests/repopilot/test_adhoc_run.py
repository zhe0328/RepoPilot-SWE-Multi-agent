"""Tests for Adhoc Phase C: repo resolution and ephemeral adhoc runs."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from repopilot.eval.adhoc import is_adhoc_record
from repopilot.eval.loader import RunRecord, discover_all_run_paths, resolve_task_run_dir
from repopilot.runner.adhoc_run import (
    make_adhoc_task_id,
    run_adhoc_task,
    write_adhoc_task_dir,
)
from repopilot.runner.repo_resolve import is_repo_url, materialize_git_repo
from repopilot.schema import load_task_config

ROOT = Path(__file__).resolve().parents[2]
ADHOC_FIXTURE = ROOT / "benchmarks" / "adhoc_parser_empty" / "fixture"
ADHOC_ISSUE = ROOT / "benchmarks" / "adhoc_parser_empty" / "issue.md"
TEST_CMD = (
    "PYTHONPATH=benchmarks/adhoc_parser_empty/fixture "
    "python -m pytest benchmarks/adhoc_parser_empty/fixture/tests/test_repro.py -v"
)


def test_is_repo_url():
    assert is_repo_url("https://github.com/org/repo.git")
    assert is_repo_url("git@github.com:org/repo.git")
    assert not is_repo_url("/tmp/local-repo")
    assert not is_repo_url("benchmarks/adhoc_parser_empty/fixture")


def test_make_adhoc_task_id():
    task_id = make_adhoc_task_id("https://github.com/acme/widget.git")
    assert task_id.startswith("adhoc_widget_")


def test_write_adhoc_task_dir(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    issue = tmp_path / "issue.md"
    issue.write_text("# bug\n")
    write_adhoc_task_dir(
        tmp_path / "task",
        task_id="adhoc_demo_001",
        repo_path=repo,
        base_commit="abc123",
        issue_path=issue,
        test_command="pytest -q",
        tests_tag="tests_preexisting",
    )
    task_dir = tmp_path / "task"
    assert (task_dir / "issue.md").read_text() == "# bug\n"
    cfg = yaml.safe_load((task_dir / "config.yaml").read_text())
    assert cfg["task_id"] == "adhoc_demo_001"
    assert cfg["repo"]["path"] == str(repo)
    assert cfg["eval"]["tags"] == ["adhoc", "tests_preexisting"]


@pytest.mark.skipif(not ADHOC_FIXTURE.is_dir(), reason="requires adhoc_parser_empty fixture")
@patch("repopilot.runner.repo_resolve.subprocess.run")
def test_materialize_git_repo_from_non_git_fixture(mock_run, tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n")
    cache = tmp_path / "cache"

    def _fake_run(cmd, **kwargs):
        cwd = Path(kwargs["cwd"])
        if cmd[:2] == ["git", "init"]:
            (cwd / ".git").mkdir()
        return type("R", (), {"returncode": 0, "stdout": "abc123def456789012345678901234567890abcd\n"})()

    mock_run.side_effect = _fake_run
    repo_path = materialize_git_repo(tmp_path / "src", cache)
    assert (repo_path / ".git").is_dir()
    assert (repo_path / "app.py").read_text() == "x = 1\n"


@pytest.mark.skipif(not ADHOC_FIXTURE.is_dir(), reason="requires adhoc_parser_empty fixture")
@patch("repopilot.runner.run_task.shutil.which", return_value="/usr/bin/mini")
def test_run_adhoc_task_dry_run(_which, tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "runs").mkdir()
    repo_path = tmp_path / "cached_repo"
    repo_path.mkdir()
    issue = root / "issue.md"
    issue.write_text("# repro\n")

    with patch("repopilot.runner.adhoc_run.make_adhoc_task_id", return_value="adhoc_fixture_test"):
        with patch("repopilot.runner.adhoc_run.resolve_repository", return_value=repo_path):
            with patch("repopilot.runner.adhoc_run.resolve_git_ref", return_value="abc123"):
                result = run_adhoc_task(
                    str(ADHOC_FIXTURE),
                    issue,
                    test_command="pytest -q",
                    project_root=root,
                    dry_run=True,
                )

    assert result.task_id == "adhoc_fixture_test"
    assert result.output_dir == (root / "runs" / "adhoc" / "adhoc_fixture_test").resolve()
    task_cfg = load_task_config(
        yaml.safe_load((result.output_dir / "config.yaml").read_text()),
        task_dir=result.output_dir,
    )
    assert task_cfg.eval.failure_mode == "adhoc"
    assert "adhoc" in task_cfg.eval.tags


def test_discover_runs_adhoc_subdirectory(tmp_path):
    adhoc_run = tmp_path / "adhoc" / "adhoc_demo_001"
    adhoc_run.mkdir(parents=True)
    (adhoc_run / "trace.json").write_text(json.dumps({"task_id": "adhoc_demo_001"}))
    benchmark_run = tmp_path / "task_001_sudoku"
    benchmark_run.mkdir()
    (benchmark_run / "trace.json").write_text(json.dumps({"task_id": "task_001_sudoku"}))

    paths = discover_all_run_paths(tmp_path)
    assert (adhoc_run, "latest") in paths
    assert (benchmark_run, "latest") in paths


def test_resolve_task_run_dir_under_adhoc(tmp_path):
    adhoc_run = tmp_path / "adhoc" / "adhoc_demo_001"
    adhoc_run.mkdir(parents=True)
    (adhoc_run / "trace.json").write_text("{}")

    resolved = resolve_task_run_dir(tmp_path, "adhoc_demo_001")
    assert resolved == adhoc_run


def test_is_adhoc_record_from_runs_adhoc_parent(tmp_path):
    run_dir = tmp_path / "adhoc" / "adhoc_demo_001"
    run_dir.mkdir(parents=True)
    record = RunRecord(
        task_id="adhoc_demo_001",
        agent_mode="baseline",
        model="m",
        run_dir=run_dir,
        eval_tags=[],
        failure_mode=None,
    )
    assert is_adhoc_record(record)
