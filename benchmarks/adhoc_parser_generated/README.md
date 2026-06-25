# Adhoc Phase D — agent-authored repro tests

Same buggy parser as [`adhoc_parser_empty`](../adhoc_parser_empty/), but **no `fixture/tests/`** at `base_commit`. The agent must write repro pytest before fixing the bug.

| Phase | Tests | Tag |
|-------|-------|-----|
| A (`adhoc_parser_empty`) | QA pre-wrote `test_repro.py` | `tests_preexisting` |
| **D (this task)** | **Agent creates** `test_repro.py` | `tests_generated` |

## One-time setup

```bash
git add benchmarks/adhoc_parser_generated/
git commit -m "Add adhoc Phase D demo: parser bug, no pre-written tests"

python benchmarks/adhoc_parser_generated/pin_base_commit.py
```

## Run

```bash
# Before agent: verify fails (test file does not exist yet)
repopilot run adhoc_parser_generated --skip-mini

# Full run: agent writes tests + fix
repopilot run adhoc_parser_generated

repopilot eval view adhoc_parser_generated --open
```

Trace records `task_tags.tests_authored_by: agent` and `patch.test_files_added` when the agent adds test files.

## Success criteria

- Runner verify passes (`tests_passed: true`)
- `patch.diff` adds `fixture/tests/test_repro.py` (or equivalent under task path)
- `run_meta.yaml` → `generated_tests_ok: true`
