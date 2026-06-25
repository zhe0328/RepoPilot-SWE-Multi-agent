# Adhoc task template

Copy this directory to `benchmarks/adhoc_<name>/` and customize.

## Layout

### Phase A — pre-written repro tests (`tests_preexisting`)

```text
benchmarks/adhoc_<name>/
  config.yaml
  issue.md
  pin_base_commit.py
  fixture/
    ...                 # buggy code at base_commit
    tests/
      test_repro.py     # QA-authored (fails before fix)
      conftest.py
```

See [adhoc_parser_empty/README.md](../adhoc_parser_empty/README.md).

### Phase D — agent writes repro tests (`tests_generated`)

```text
benchmarks/adhoc_<name>/
  config.yaml           # tags: [adhoc, tests_generated]
  issue.md              # copy from issue.generated.example.md
  pin_base_commit.py
  fixture/
    ...                 # buggy code only — NO tests/ directory
```

See [adhoc_parser_generated/README.md](../adhoc_parser_generated/README.md).

## Checklist (Phase A)

1. Copy `_template_adhoc` → `adhoc_<name>`; copy `config.yaml.example` → `config.yaml`
2. Put buggy code under `fixture/`; write `fixture/tests/test_repro.py`
3. Commit; run `pin_base_commit.py`
4. `repopilot run adhoc_<name> --skip-mini` → verify **fail**
5. `repopilot run adhoc_<name>` → agent demo

## Checklist (Phase D)

1. Copy structure from `adhoc_parser_generated` (no `fixture/tests/`)
2. Set `tests_generated` in config; use `issue.generated.example.md` as issue template
3. `test_command` must point at the path the agent is told to create
4. Commit; pin `base_commit`
5. `--skip-mini` → verify **fail** (missing test file)
6. Full run → expect `patch.test_files_added` + `generated_tests_ok: true` in run_meta

**Eval:** Adhoc runs stay in a separate bucket from formal `task_*` benchmarks.
