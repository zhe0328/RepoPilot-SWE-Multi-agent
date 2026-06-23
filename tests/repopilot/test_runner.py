from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

from repopilot.runner.run_task import (
    _stage_setup_patch,
    build_mini_command,
    resolve_task_dir,
    run_benchmark_task,
)
from repopilot.schema import load_task

ROOT = Path(__file__).resolve().parents[2]
BENCHMARKS = ROOT / "benchmarks"
TASK_001 = BENCHMARKS / "task_001_sudoku"


def test_resolve_task_dir_by_name():
    assert resolve_task_dir(Path("task_001_sudoku"), benchmarks_root=BENCHMARKS) == TASK_001.resolve()


def test_resolve_task_dir_by_path():
    assert resolve_task_dir(TASK_001) == TASK_001.resolve()


def test_resolve_task_dir_missing():
    with pytest.raises(FileNotFoundError):
        resolve_task_dir(Path("no_such_task"), benchmarks_root=BENCHMARKS)


@patch("repopilot.runner.run_task.shutil.which", return_value="/usr/bin/mini")
def test_build_mini_command(_which):
    task = load_task(TASK_001)
    cmd = build_mini_command(task, Path("runs/task_001_sudoku/trajectory.traj.json"))
    assert cmd[0] == "/usr/bin/mini"
    assert "-t" in cmd
    assert "upstream/tests/run/test_sudoku.py" in cmd[cmd.index("-t") + 1]
    assert cmd[-2:] == ["-o", "runs/task_001_sudoku/trajectory.traj.json"]
    assert "-y" in cmd
    assert "--exit-immediately" in cmd


@patch("repopilot.runner.run_task.shutil.which", return_value="/usr/bin/mini")
def test_run_benchmark_task_dry_run(_which, capsys):
    result = run_benchmark_task(TASK_001, project_root=ROOT, dry_run=True)
    assert result.task_id == "task_001_sudoku"
    assert result.mini_exit_code is None
    assert "/usr/bin/mini" in result.mini_command[0]
    captured = capsys.readouterr()
    assert "task_001_sudoku" in captured.out


def test_stage_setup_patch_copies_to_temp():
    patch_path = TASK_001 / "setup.patch"
    staged = _stage_setup_patch(patch_path)
    try:
        assert staged is not None
        assert staged.is_file()
        assert staged.read_bytes() == patch_path.read_bytes()
    finally:
        staged.unlink(missing_ok=True)


@contextmanager
def _noop_workspace(*_args, **_kwargs):
    yield


@patch("repopilot.runner.run_task.run_verification", return_value=1)
@patch("repopilot.runner.run_task.prepared_workspace")
@patch("repopilot.runner.run_task.shutil.which", return_value="/usr/bin/mini")
def test_skip_mini_skips_agent_and_records_verify_failure(_which, mock_workspace, _verify):
    mock_workspace.side_effect = lambda *args, **kwargs: _noop_workspace()
    result = run_benchmark_task(
        TASK_001,
        project_root=ROOT,
        skip_mini=True,
        restore_workspace=True,
    )
    assert result.mini_exit_code is None
    assert result.tests_passed is False
    assert result.test_exit_code == 1
    assert (result.output_dir / "verify_test.log").is_file()
    assert (result.output_dir / "run_meta.yaml").is_file()
