# RepoPilot

**Execution-grounded SWE agent evaluation** built on [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent).

RepoPilot is not primarily a new coding agent or multi-agent demo. It is a **trace-based evaluation harness** that runs benchmark and adhoc tasks, records structured trajectories, attributes failures from pytest output, and produces aggregate comparison reports—so you can answer *why* an agent succeeded or failed, *at which step*, *on which files*, and *at what cost*.

Upstream `mini` remains the baseline agent. RepoPilot adds orchestration, trace recording, eval, and HTML trajectory views on top.

## What you get

| Layer | Status | Description |
|-------|--------|-------------|
| **Run** | Done | Benchmark runner + adhoc (local fixture or external git repo) with worktree isolation |
| **Trace** | Done (v2) | `trace.json`, failure attribution, patch/test extraction, stage labels |
| **Eval** | Done | Summary, compare, breakdown; benchmark vs adhoc buckets |
| **Visualize** | Done | Repair-loop Mermaid, HTML run views (`eval view`), collapsed step timeline |
| **Self-repair / roles** | Deferred | Optional experiments, eval-gated |

## Project layout

```text
RepoPilot-SWE-Multi-agent/
├── upstream/              # Frozen mini-swe-agent (baseline reference)
├── src/repopilot/         # Runner, schema, trace, eval, visualize
├── benchmarks/
│   ├── task_001–014/      # Formal benchmark suite (tagged failure modes)
│   └── adhoc_*/           # User-reported bug demos (not in benchmark metrics)
├── tests/repopilot/       # RepoPilot unit tests
├── scripts/               # Patch verification, baseline extraction
└── runs/                  # Run outputs (gitignored)
    ├── {task_id}/         # benchmark + fixed adhoc task runs
    ├── adhoc/{task_id}/   # ephemeral external-repo adhoc runs
    └── eval/              # aggregate reports + per-run view.html
```

See [benchmarks/README.md](benchmarks/README.md) for the full task catalog and schema.

## Install

```bash
python3 -m venv venv && source venv/bin/activate

pip install -e 'upstream/[dev]'
pip install -e '.[dev]'
```

Configure model access (same as upstream mini):

```bash
export OPENAI_API_KEY=...
# optional: export OPENAI_BASE_URL=... MSWEA_MODEL_NAME=...
```

Verify:

```bash
mini --help
repopilot --help
python -m pytest tests/repopilot -q
```

## Quick start

### Benchmark tasks

```bash
repopilot run task_001_sudoku
repopilot run task_001_sudoku --dry-run
repopilot run task_001_sudoku --skip-mini    # harness only, no LLM
```

### Adhoc tasks (user-reported bugs)

Fixed task directories under `benchmarks/adhoc_*`:

| Task | Mode | Notes |
|------|------|-------|
| `adhoc_parser_empty` | Phase A | QA pre-wrote repro tests (`tests_preexisting`) |
| `adhoc_parser_generated` | Phase D | Agent writes repro tests (`tests_generated`) |
| `adhoc_coach_agent` | Phase C | External repo via `repo_url` |

```bash
repopilot run adhoc_parser_empty
repopilot run adhoc_parser_generated          # mini authors test_repro.py + fix
repopilot run adhoc_coach_agent               # clones coach-agent, smoke/strict verify
```

Ephemeral run against any local path or git URL (outputs under `runs/adhoc/`):

```bash
repopilot adhoc run https://github.com/org/repo.git issue.md \
  --test-cmd "pytest -q" --commit main
```

See [benchmarks/adhoc_parser_empty/README.md](benchmarks/adhoc_parser_empty/README.md), [benchmarks/adhoc_parser_generated/README.md](benchmarks/adhoc_parser_generated/README.md), and [benchmarks/adhoc_coach_agent/README.md](benchmarks/adhoc_coach_agent/README.md).

### Trace & eval

```bash
repopilot trace runs/task_001_sudoku/trajectory.traj.json

repopilot eval summary                         # benchmark only (default)
repopilot eval summary --adhoc-only            # adhoc bucket only
repopilot eval view adhoc_parser_generated --open   # HTML trajectory report
```

## Benchmarks

14 reproducible `task_*` benchmarks with tagged failure modes:

| Tier | Tasks | Notes |
|------|-------|-------|
| Single-bug | `task_001`–`task_010` | off-by-one, wrong operator, import path, logic, etc. |
| Multi-bug | `task_011` (3), `task_012` (4), `task_013`/`task_014` (5) | `eval.bug_count` + `failure_mode: composite` |

Each task has `config.yaml`, `issue.md`, and optional `setup.patch` (plants a known bug at `base_commit`).

### Run artifacts

```text
runs/{task_id}/
  trajectory.traj.json   # upstream mini trajectory
  trace.json             # structured trace (schema v2)
  patch.diff             # extracted patch (includes new files after agent run)
  test.log               # pytest from trajectory + runner verify
  final_report.md
  failure_reason.md      # if failed
  run_meta.yaml          # includes generated_tests for Phase D
```

Apply a fix to your own repo manually: `git apply runs/.../patch.diff` (not pushed automatically).

## CLI reference

```bash
# Benchmark
repopilot run <task_id> [--dry-run] [--skip-mini] [--no-restore]

# Adhoc (fixed task dir or ephemeral)
repopilot run --adhoc <repo> --issue issue.md --test-cmd "pytest -q"
repopilot adhoc run <repo> issue.md --test-cmd "pytest -q" [--commit SHA] [--tests-tag tests_generated]

repopilot trace <trajectory.traj.json> [-o output_dir]

repopilot eval summary [--runs-dir runs] [--benchmark-only|--include-adhoc|--adhoc-only]
repopilot eval compare [--task task_id]
repopilot eval breakdown [--by failure_mode|difficulty|failure_category|failure_stage]
repopilot eval view <task_id|run_dir> [--open]
```

`repopilot-baseline` is an alias entry point with the same commands.

## Trace & eval highlights

Trace v2 records per step:

- Inferred **stages** (`read`, `edit`, `test`, `submit`) from shell commands
- Tool calls, files touched, pytest runs before/after edits
- Failure fields: `failure_category`, `failure_stage`, `failed_step`, `failure_message`
- Task tags: `failure_mode`, `difficulty`, `bug_count`, `verify_tier`, `tests_authored_by`

HTML reports show a **repair loop** (retry edges after failed tests) and a collapsible **step timeline**. Adhoc runs are reported in a separate eval bucket so they do not dilute benchmark success rates.

## Development

```bash
python -m pytest tests/repopilot -q
python scripts/verify_benchmark_patches.py
cd upstream && python -m pytest tests -q   # optional upstream tests
```

**Style:** Python 3.10+, type hints, `pathlib`, `typer`, `pytest`. Keep changes minimal and eval-first—new agent features should be justified by measurable eval improvement.

## Upstream

The baseline agent lives in [`upstream/`](upstream/) (mini-swe-agent v2.4.2). See [upstream/README.md](upstream/README.md) and [mini-swe-agent docs](https://mini-swe-agent.com/latest/) for agent internals, model config, and sandbox options.

## References

- [benchmarks/README.md](benchmarks/README.md) — task catalog, adhoc phases, schema
- [SWE-agent paper](https://arxiv.org/abs/2405.15793) — upstream attribution
