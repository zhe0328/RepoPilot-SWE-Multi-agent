"""Validate agent-authored repro tests (Adhoc Phase D)."""

from __future__ import annotations

from repopilot.schema import TaskConfig
from repopilot.trace.parse import analyze_patch_test_files

TESTS_GENERATED_TAG = "tests_generated"


def is_tests_generated_task(task: TaskConfig) -> bool:
    return TESTS_GENERATED_TAG in (task.eval.tags or [])


def assess_generated_tests(
    task: TaskConfig,
    patch_text: str,
    *,
    tests_passed: bool,
) -> dict[str, object]:
    """Return metadata about agent-authored tests for tests_generated tasks."""
    if not is_tests_generated_task(task):
        return {}

    meta = analyze_patch_test_files(patch_text or "")
    added = meta.get("test_files_added") or []
    touched = meta.get("test_files_touched") or []
    present = bool(added or touched)
    # On success, expect at least one new/touched test file in the patch.
    ok = present if tests_passed else True

    return {
        "tests_tag": TESTS_GENERATED_TAG,
        "test_files_added": added,
        "test_files_touched": touched,
        "generated_tests_present": present,
        "generated_tests_ok": ok,
    }
