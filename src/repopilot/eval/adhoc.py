"""Adhoc run detection and partitioning (Adhoc Phase B)."""

from __future__ import annotations

from repopilot.eval.loader import RunRecord

ADHOC_EVAL_TAG = "adhoc"


def is_adhoc_record(record: RunRecord) -> bool:
    """True when a run is tagged or named as an adhoc (non-benchmark) task."""
    if record.run_dir.parent.name == "adhoc":
        return True
    if record.task_id.startswith("adhoc_"):
        return True
    if record.failure_mode == "adhoc":
        return True
    return ADHOC_EVAL_TAG in record.eval_tags


def partition_runs(records: list[RunRecord]) -> tuple[list[RunRecord], list[RunRecord]]:
    benchmark: list[RunRecord] = []
    adhoc: list[RunRecord] = []
    for record in records:
        (adhoc if is_adhoc_record(record) else benchmark).append(record)
    return benchmark, adhoc
