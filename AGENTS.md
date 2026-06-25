# RepoPilot agent guide

Guidance for AI assistants working in this repository.

## What this repo is

**RepoPilot** extends [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) with a **trace-based evaluation harness**. The primary artifact is measurable, comparable runs—not a multi-agent demo.

- **Upstream agent:** `upstream/` — frozen mini-swe-agent; baseline runs call `mini` via subprocess.
- **RepoPilot code:** `src/repopilot/` — schema, runner, trace recorder, eval harness, visualization.
- **Formal benchmarks:** `benchmarks/task_*` — 14 tagged tasks (single- and multi-bug).
- **Adhoc tasks:** `benchmarks/adhoc_*` — user-reported bugs; **excluded** from benchmark success-rate by default.
- **Outputs:** `runs/` — gitignored; never commit unless the user asks.
- **Plan docs:** `Plan.md` is gitignored locally; do not commit unless the user asks.

Read [README.md](README.md) for install/CLI; [benchmarks/README.md](benchmarks/README.md) for task catalog.

## Architecture

```text
Run (runner)  →  Trace (recorder)  →  Eval (loader/metrics/report/view)  →  Agent experiments (deferred)
```

**Eval-first rule:** extend trace schema and eval metrics before adding agent features (self-repair, role splits). New agent behavior must be justified by eval comparison.

**Agent boundary:** `agent.mode: baseline` runs upstream `mini`. `agent.mode: repopilot` is **not implemented** yet. Phase D “agent writes tests” means **mini** writes tests per issue prompt—not a RepoPilot agent.

## Project structure

```text
src/repopilot/
  schema/           TaskConfig (Pydantic), discover_tasks (task_* only), load_task
  runner/
    run_task.py     worktree lifecycle, verify, trace recording
    benchmark.py    CLI (run, trace, eval, adhoc)
    adhoc_run.py    ephemeral adhoc tasks → runs/adhoc/{id}/
    repo_resolve.py clone/cache local or remote repos (Phase C)
    generated_tests.py  Phase D patch validation (tests_generated)
  trace/            parse (stages, pytest, patch), classify, recorder (v2)
  eval/
    loader.py       RunRecord, discover_all_run_paths (incl. runs/adhoc/)
    adhoc.py        partition_runs, is_adhoc_record
    metrics, report, compare, failure_analysis, trajectory_analysis
    visualize.py    Mermaid repair loop, HTML view.html

benchmarks/
  task_XXX_name/    formal suite — config.yaml, issue.md, setup.patch
  adhoc_*/          adhoc demos — no setup.patch; see phase notes below
  _template_adhoc/  copy for new adhoc cases

tests/repopilot/    RepoPilot tests only
```

## Adhoc phases (summary)

| Phase | Example | Key idea |
|-------|---------|----------|
| A | `adhoc_parser_empty` | Pre-written repro tests (`tests_preexisting`) |
| B | eval harness | `--benchmark-only` / `--adhoc-only`; tags in trace |
| C | `adhoc_coach_agent`, `repopilot adhoc run` | External `repo_url`, cache under `runs/.cache/repos/` |
| D | `adhoc_parser_generated` | No tests at base_commit; mini writes tests (`tests_generated`) |

Adhoc task config uses `eval.tags: [adhoc, tests_preexisting|tests_generated]`, optional `verify_tier: strict|smoke`. External-repo adhoc may use smoke verify when no pytest exists.

## Common commands

```bash
pip install -e 'upstream/[dev]' && pip install -e '.[dev]'

# Benchmark
repopilot run task_001_sudoku
repopilot run task_011_sudoku_multi3 --skip-mini

# Adhoc (fixed task dir)
repopilot run adhoc_parser_empty
repopilot run adhoc_parser_generated
repopilot run adhoc_coach_agent

# Adhoc (ephemeral external repo)
repopilot adhoc run <repo_url> issue.md --test-cmd "pytest -q" --commit main

# Eval & views
repopilot eval summary                    # benchmark only by default
repopilot eval summary --adhoc-only
repopilot eval view adhoc_parser_generated --open
repopilot trace runs/<task_id>/trajectory.traj.json

python -m pytest tests/repopilot -q
python scripts/verify_benchmark_patches.py
```

## Coding conventions

Inherited from upstream mini-swe-agent, adapted for RepoPilot:

1. Target Python 3.10+; use `list` not `List`, `pathlib` not `os.path`.
2. Use `typer` for CLI; `pydantic` v2 for config models.
3. Keep code minimal—prefer focused diffs over abstractions.
4. Do not catch exceptions unless explicitly required.
5. Comments only for non-obvious logic.
6. Tests: `pytest` only; avoid mocking unless asked; no trivial assertions.
7. `pytest.mark.parametrize` first arg must be a **tuple**, second a **list**.

## Where to change what

| Task | Location |
|------|----------|
| Add formal benchmark task | `benchmarks/task_XXX/`, `benchmarks/README.md`, `test_task_schema.py`, `scripts/verify_benchmark_patches.py` |
| Add adhoc task | `benchmarks/adhoc_<name>/`, pin with `pin_base_commit.py`, update `benchmarks/README.md` |
| Run lifecycle / worktree | `src/repopilot/runner/run_task.py` |
| External repo / adhoc CLI | `repo_resolve.py`, `adhoc_run.py`, `benchmark.py` |
| Phase D generated tests | `generated_tests.py`, `trace/parse.py` (`capture_workspace_diff`) |
| CLI commands | `src/repopilot/runner/benchmark.py` |
| Trace schema / stages / failure taxonomy | `src/repopilot/trace/` |
| Eval aggregation / adhoc split | `src/repopilot/eval/`, especially `adhoc.py`, `loader.py`, `report.py` |
| HTML / Mermaid views | `src/repopilot/eval/visualize.py` |
| Task config fields | `src/repopilot/schema/task.py` → wire through `recorder.py`, `loader.py`, `run_task.py` |

## Benchmark task rules

- `task_id` in `config.yaml` must match the directory name.
- `discover_tasks()` returns only `task_*` directories—not adhoc.
- `repo.base_commit` is checked out in an isolated git worktree under `runs/{task_id}/.workspace`.
- `setup.patch` must apply cleanly and cause pytest to **fail** before the agent runs.
- Tag with `eval.failure_mode`, `eval.difficulty`; multi-bug tasks use `eval.bug_count` and `tags: [multi_bug]`.
- Do not edit upstream source for benchmarks—use `setup.patch` to inject bugs.

## Adhoc task rules

- **No `setup.patch`** — buggy code is committed in `fixture/` (local) or pinned via `repo_url` + `base_commit` (external).
- Phase A/D local demos: run `pin_base_commit.py` after committing the task directory.
- Phase D: omit `fixture/tests/` at `base_commit`; issue must instruct mini to create repro pytest.
- `test_command` in config is runner verify **after** mini finishes; `--skip-mini` may fail if tests do not exist yet (expected for Phase D).
- Patches land in `runs/.../patch.diff`; **not** auto-pushed to external repos.
- `capture_workspace_diff` uses `git add -N` so new test files appear in patch metadata.

## Git & commits

- Only commit when the user explicitly asks.
- Do not commit `runs/`, `.env`, `Plan.md`, or credentials.
- Prefer conventional prefixes: `feat(eval):`, `fix(trace):`, `docs:`, etc.
- Do **not** add `Co-authored-by: Cursor` trailers.

## Phase status (summary)

| Phase | Status |
|-------|--------|
| 0–1 | Done — baseline, schema, runner |
| 2–3 | Done — trace v2, failure attribution |
| 4 | Done — eval compare, breakdown, exemplars |
| 5 | Done — repair-loop viz, HTML `eval view`, stage classification |
| Adhoc A–D | Done — preexisting tests, eval split, external repo CLI, agent-written tests |
| 6+ | Deferred — `repopilot` agent mode, self-repair, roles, Docker |

## Upstream boundary

- Do **not** mix RepoPilot logic into `upstream/` unless fixing a deliberate upstream fork change.
- Baseline agent behavior = unmodified `mini` from `upstream/`.
- Upstream docs: `upstream/docs/`; upstream tests: `upstream/tests/`.
