# Adhoc task template

Copy this directory to `benchmarks/adhoc_<name>/` and customize.

## Layout

```text
benchmarks/adhoc_<name>/
  config.yaml           # no setup.patch; pin base_commit after commit
  issue.md              # user symptom + instructions
  pin_base_commit.py    # copy from adhoc_parser_empty
  fixture/
    ...                 # buggy application code (already broken at base_commit)
    tests/
      test_repro.py     # pre-authored repro tests (Phase A)
      conftest.py       # adds fixture/ to PYTHONPATH
```

## Checklist

1. Copy `_template_adhoc` → `adhoc_<name>`; rename `adhoc_EXAMPLE` paths in config/issue
2. Put **buggy** code under `fixture/` (no setup.patch)
3. Write `fixture/tests/test_repro.py` (1–3 cases that fail before fix)
4. Commit the task directory
5. Run `python benchmarks/adhoc_<name>/pin_base_commit.py`
6. `repopilot run adhoc_<name> --skip-mini` → verify should **fail**
7. `repopilot run adhoc_<name>` → full agent demo

See [adhoc_parser_empty/README.md](../adhoc_parser_empty/README.md) for a working example.

**Eval:** Adhoc runs are not mixed into benchmark success rates until [Adhoc Phase B](../../Plan.md#adhoc-phase-b--harness-extensions-small-pr).
