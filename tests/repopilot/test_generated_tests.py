"""Tests for Adhoc Phase D — agent-authored repro tests."""

from __future__ import annotations

from repopilot.runner.generated_tests import assess_generated_tests, is_tests_generated_task
from repopilot.schema.task import AgentConfig, EvalTags, RepoConfig, TaskConfig


def _task_with_tags(*tags: str) -> TaskConfig:
    return TaskConfig(
        task_id="adhoc_demo",
        repo=RepoConfig(path=".", base_commit="abc"),
        issue_file="issue.md",
        test_command="pytest -q",
        agent=AgentConfig(mode="baseline"),
        eval=EvalTags(failure_mode="adhoc", tags=list(tags)),
    )


def test_is_tests_generated_task():
    assert is_tests_generated_task(_task_with_tags("adhoc", "tests_generated"))
    assert not is_tests_generated_task(_task_with_tags("adhoc", "tests_preexisting"))


def test_assess_generated_tests_success():
    task = _task_with_tags("adhoc", "tests_generated")
    patch = (
        "diff --git a/benchmarks/adhoc_parser_generated/fixture/tests/test_repro.py "
        "b/benchmarks/adhoc_parser_generated/fixture/tests/test_repro.py\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/benchmarks/adhoc_parser_generated/fixture/tests/test_repro.py\n"
        "+def test_empty():\n"
        "+    assert True\n"
    )
    result = assess_generated_tests(task, patch, tests_passed=True)
    assert result["generated_tests_present"] is True
    assert result["generated_tests_ok"] is True
    assert result["test_files_added"]


def test_assess_generated_tests_missing_on_success():
    task = _task_with_tags("adhoc", "tests_generated")
    patch = (
        "diff --git a/foo.py b/foo.py\n"
        "--- a/foo.py\n"
        "+++ b/foo.py\n"
        "+# fix only\n"
    )
    result = assess_generated_tests(task, patch, tests_passed=True)
    assert result["generated_tests_present"] is False
    assert result["generated_tests_ok"] is False


def test_assess_generated_tests_skipped_for_preexisting():
    task = _task_with_tags("adhoc", "tests_preexisting")
    assert assess_generated_tests(task, "diff --git a/t b/t\n", tests_passed=True) == {}


def test_trace_tags_tests_authored_by_agent():
    from pathlib import Path

    from repopilot.trace.recorder import TraceContext, build_trace_document

    traj = {
        "messages": [],
        "info": {
            "exit_status": "Submitted",
            "model_stats": {"api_calls": 0, "instance_cost": 0.0},
            "config": {"model": {"model_name": "test-model"}},
        },
    }
    ctx = TraceContext(
        task_id="adhoc_parser_generated",
        eval_tags=["adhoc", "tests_generated"],
        tests_passed=True,
    )
    doc = build_trace_document(traj, ctx=ctx, traj_path=Path("trajectory.traj.json"))
    assert doc["task_tags"]["tests_authored_by"] == "agent"
    assert "tests_generated" in doc["task_tags"]["tags"]
