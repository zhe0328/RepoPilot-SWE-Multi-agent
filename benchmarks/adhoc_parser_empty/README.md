# Adhoc demo — empty parser crash

**Phase A** user-reported bug demo. Not part of the formal `task_001`–`task_014` benchmark suite.

## Story

| Step | What happens |
|------|----------------|
| User report | Empty CSV input raises `ValueError` instead of returning `[]` |
| QA | Pre-wrote `fixture/tests/test_repro.py` (no agent-authored tests in this demo) |
| Agent | Reads issue + failing tests, fixes `list_parser.py` |
| Runner | Independent pytest verify (same as benchmark tasks) |

**No `setup.patch`** — the buggy code lives in `fixture/list_parser.py` at `base_commit`.

## One-time setup (commit the fixture)

The runner uses a git worktree at `base_commit`. The fixture **must be committed** before `repopilot run`:

```bash
git add benchmarks/adhoc_parser_empty/
git commit -m "Add adhoc Phase A demo: parser empty-input bug"

python benchmarks/adhoc_parser_empty/pin_base_commit.py
```

## Verify harness (expect verify **fail** before agent)

```bash
repopilot run adhoc_parser_empty --skip-mini
# verify exit code: 1 (test_repro fails on buggy code)
```

## Run agent demo

```bash
repopilot run adhoc_parser_empty
repopilot eval view adhoc_parser_empty --open
```

## Eval note (until Adhoc Phase B)

Outputs go to `runs/adhoc_parser_empty/`. **`repopilot eval summary` will include this run** alongside benchmark tasks. Treat adhoc separately when reporting benchmark success rates, or omit this directory before aggregating.

## Expected fix

Remove the `raise ValueError` on empty string; return `[]` instead.
