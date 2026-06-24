# RepoPilot Plan

> Execution-Grounded SWE Agent — derived from [repopilot_swe_agent_mvp_plan.md](repopilot_swe_agent_mvp_plan.md)

## Goal

Build **RepoPilot**, an execution-grounded software engineering evaluation system on top of [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent), that turns agent runs into **structured, analyzable, and comparable evidence**: trajectories, test logs, failure attribution, and aggregate reports.

The project is **not** primarily a multi-agent demo or a new coding agent. The differentiator is an **evaluation harness** that mature coding agents lack: the ability to systematically answer **why an agent succeeded or failed, at which step, on which files, what it cost, and how runs compare**—grounded in pytest output and structured traces, not LLM self-judgment. **Complex code scenarios** are handled by richer trace/eval analysis and benchmark design—not by mandatory Planner/Coder/Tester role splits.

**One-line summary:** Extend mini-swe-agent with deep trace recording and a trace-based evaluation harness (analyze, quantify, visualize); treat self-repair and role separation as optional Layer E experiments, only if eval shows measurable benefit.

**North star question:** For every benchmark run, can we produce a structured answer to all six audit questions below?

---

## Objectives

| # | Objective | Why it matters |
|---|-----------|----------------|
| 1 | **Evaluation harness** | Batch-run benchmarks; aggregate metrics; explain success/failure per task—**primary resume/demo artifact** |
| 2 | **Trace observability** | Record steps, tool calls, diffs, test logs, file targets, and cost so eval can attribute failures in **complex scenarios** |
| 3 | **Failure attribution** | For every run: `failure_category`, `failure_stage`, `failed_step`, and human-readable **failure reason** grounded in pytest |
| 4 | **Trajectory analysis & visualization** | Quantify step timelines, tool usage, test pre/post deltas; render drill-down reports and (later) interactive views |
| 5 | **Baseline comparison** | Run upstream mini-swe-agent on identical tasks/config and compare fairly across runs and tasks |
| 6 | **Execution-grounded validation** | Use pytest results—not LLM self-judgment—to decide if a patch works |
| 7 | **Issue-to-patch workflow** | Turn a GitHub issue + repo commit into a verifiable code fix (via upstream `mini` in baseline mode) |
| 8 | **Test-driven self-repair** *(optional, Layer E)* | Multi-round repair only if harness needs it for comparison experiments—**measured** vs baseline |
| 9 | **Role separation** *(optional, Layer E)* | Planner / Coder / Tester split **only** where eval shows a specific stage bottleneck—not an MVP requirement |

**Positioning vs. a generic coding chatbot:** RepoPilot is a **trace-based evaluation system** for SWE agents. Harness depth (analyze, quantify, visualize) comes first; agent features (self-repair, roles) are experiments the harness must justify.

**What commercial coding agents typically cannot answer systematically:**

| Question | RepoPilot target |
|----------|------------------|
| Why did this agent succeed? | `outcome`, success stage, final patch, post-fix test log |
| Why did it fail? | `failure_category`, `failure_message`, last failing test |
| Which step failed? | `failed_step`, `failure_stage`, step timeline in `trace.json` |
| Did self-repair help? | Round-by-round test status, Δ success vs baseline, cost per extra fix |
| What did it cost? | API calls, tokens, `$`, runtime per run |
| How does baseline compare? | Side-by-side per `task_id` in `eval_report.md` / `comparison_table.csv` |

---

## MVP Scope

### In scope

- Python repos only
- pytest only
- Local repo path or cloned GitHub repo (isolated via **git worktree** so dev checkout is untouched)
- **5–10** mini benchmark tasks, each tagged with **failure mode** and **expected difficulty** (see Benchmark task design below)
- Rich **trace.json** (v2) with stage labels, file targets, pytest runs, failure fields
- **Eval harness**: aggregate + per-task drill-down + failure breakdown + (Phase 4) compare across runs/modes
- **Trajectory visualization**: at minimum enhanced markdown timelines; optional React dashboard post-MVP
- Baseline runs via upstream `mini` under **identical task config**

### Out of scope (MVP)

- Mandatory Planner / Coder / Tester / Reviewer multi-agent pipeline
- Full web UI (interactive dashboard is Phase 5 / post-MVP unless a minimal static viewer ships earlier)
- Multi-language support
- Automatic PR creation
- Full SWE-bench scale
- Complex long-term memory
- Self-repair loop *(optional Layer E—defer until harness is deep enough to measure it)*
- **Adhoc user-reported bugs** *(parallel track—Phases A–D below; not mixed into benchmark success rate)*

### Inputs

```text
repo path / repo URL
base commit
issue.md
test command (e.g. pytest tests/)
expected behavior
```

### Outputs

```text
per run (under runs/{task_id}/):
  trace.json              # structured step/tool/test record (eval input)
  patch.diff
  test.log
  final_report.md         # human-readable single-run summary
  run_meta.yaml           # runner metadata (exit codes, verify result)

eval aggregate (under runs/eval/ or repo root):
  eval_report.md          # full benchmark comparison narrative
  metrics.json            # machine-readable aggregate
  comparison_table.csv
  failure_breakdown.md    # counts by failure_category
```

---

## Implementation layers (eval-first)

Build order is **not** “agent first, eval last.” Layers stack as follows:

| Layer | Phase | Purpose | Status |
|-------|-------|---------|--------|
| **A. Run infrastructure** | 1 | Reproducible tasks + runner (`repopilot run`), git worktree isolation | ✅ |
| **B. Observable run record** | 2 → 3 | `trace.json` v2; stage labels; failure taxonomy at record time | ✅ v2 |
| **C. Evaluation harness** | 2.5 → 4 | Normalize → aggregate → compare → quantify failures in complex scenarios | ✅ MVP / 🔲 full |
| **D. Visualization** | 5 | Trajectory timelines, failure charts, drill-down views | 🔲 |
| **E. Agent experiments** *(optional)* | 6–7 | Self-repair, roles—only if Layer C metrics justify the cost | 🔲 deferred |

**Primary roadmap:** deepen **B + C + D** on baseline `mini` runs first. Layer E is not required for MVP or for the core “eval harness” thesis.

Layer C already produces a **baseline-only eval report** (Phase 2.5). Next work extends trace depth and eval analysis—not agent architecture.

---

## RunRecord schema (eval canonical input)

Eval harness reads **normalized run records**, not raw trajectories. Trajectories are for debug/re-parse only.

**Phase 2 v1:** `trace.json` ≈ partial RunRecord (implemented).

**Phase 2.5+ target:** `run_record.json` per run (or normalized fields merged into `trace.json` v2):

```yaml
# runs/{task_id}/trace.json (schema_version: "1.0" → "2.0")
task_id: task_001_sudoku
agent_mode: baseline | repopilot
model: openai/gpt-5.4
outcome: success | failure | partial          # partial = agent claimed done, verify failed

# Failure attribution (required when outcome != success)
failure_category: tests_never_run | tests_still_failing | wrong_file_edited |
                  patch_empty | cost_limit_exceeded | agent_exited_early |
                  verify_mismatch | format_error | unknown
failure_stage: plan | read | edit | test | submit
failed_step: 3                                 # index into steps[]
failure_message: "1 failed, 2 passed in test_sudoku_clear_and_hint"

# Metrics (always present)
metrics:
  api_calls: 4
  instance_cost: 0.027
  repair_rounds: 1
  tests_passed: true                            # runner verify, not agent claim
  step_count: 4

steps: [...]                                    # reasoning + tool_calls + returncode
pytest_runs: [...]                              # pre_fix / post_fix logs
patch: { source, text }
retrieved_files: [...]
```

**Fair comparison rule:** baseline vs RepoPilot runs must share `task_id`, `repo.base_commit`, `test_command`, model, and cost limit. Only `agent.mode` (and later repair settings) may differ.

---

## Architecture

### Eval-centric flow

```text
benchmarks/task_XXX/config.yaml
        ↓
   Runner (baseline | repopilot)          ← Layer A
        ↓
   trajectory.traj.json (raw, debug only)
        ↓
   Trace Recorder → trace.json            ← Layer B
        ↓
   Eval Harness                           ← Layer C
     ├── normalize → RunRecord
     ├── per-task: run_summary, trajectory_analysis
     └── aggregate: eval_report, metrics.json, failure_breakdown
        ↓
   Visualization (timelines, charts)      ← Layer D
        ↓
   Agent experiments (self-repair, roles) ← Layer E, optional / eval-gated
```

### Agent pipeline (Layer E — optional, subordinate to eval)

**Default path:** upstream `mini` only (baseline mode). The pipeline below is **not** required for MVP.

```text
Issue
  → upstream mini (read / edit / test / submit in one agent)
  → Trace Recorder (every step logged for Layer B/C)
  → Eval Harness (attribute success/failure)

Optional Layer E extensions (only if eval justifies):
  → Self-repair loop (≤ 3 rounds)
  → Role split: Planner / Coder / Tester / Reviewer
```

| Module | Responsibility |
|--------|----------------|
| **Evaluation Harness** | **Primary.** Normalize runs, aggregate metrics, explain failures, compare baseline vs RepoPilot |
| **Trace Recorder** | Produce structured `trace.json` + human reports; feed eval harness |
| **Baseline Runner** | Run upstream mini unchanged; same task config as RepoPilot for fair compare |
| **Task Schema / Benchmark** | Reproducible tasks; designed with failure modes eval can distinguish |
| **Self-Repair Loop** | Apply patch → pytest → summarize failure → re-prompt; emit per-round artifacts |
| **Agent Roles** | Planner, Coder, Tester, Reviewer—add only if eval shows improvement |
| **Tool Layer** | `list_files`, `read_file`, `search_code`, `edit_file`, `run_tests`, `git_diff` |

### Target project layout

```text
repopilot/
  src/repopilot/
    agents/       planner.py, coder.py, tester.py, reviewer.py
    tools/        file_tools.py, search_tools.py, git_tools.py, test_runner.py
    eval/         runner.py, metrics.py, baseline.py
    trace/        recorder.py
    state.py, graph.py, main.py

benchmarks/
  task_001/
    config.yaml
    issue.md

runs/
  task_001_sudoku/
    trajectory.traj.json   # raw mini output (debug; gitignored)
    trace.json             # eval input (Layer B)
    patch.diff
    test.log
    final_report.md
    run_meta.yaml
  eval/
    summary/
      eval_report.md
      metrics.json
      comparison_table.csv
      failure_breakdown.md
    task_001_sudoku/
      baseline_vs_repopilot.md   # per-task drill-down
```

### Evaluation metrics

Aggregate metrics (Layer C output):

| Metric | Answers |
|--------|---------|
| Task success rate | Overall “did it work?” |
| Test pass rate (runner verify) | Ground truth vs agent self-report |
| Failure breakdown by `failure_category` | **Why** tasks fail |
| Failure breakdown by `failure_stage` | **Where** in the pipeline |
| Avg repair rounds | Self-repair depth |
| Repair effectiveness | % of round-1 fails fixed by round 2+ |
| Δ success (RepoPilot − baseline) | **Did self-repair help?** |
| Δ cost per additional success | Was extra cost worth it? |
| Avg tool calls / token cost / runtime | **What did it cost?** |
| verify_mismatch rate | Agent said done but runner pytest failed |
| Patch size | Change magnitude |

---

## Implementation Steps

### Phase 0 — Baseline: run upstream mini-swe-agent

**Goal:** Confirm the fork works end-to-end before adding RepoPilot features. No RepoPilot code yet—only upstream `mini-swe-agent`.

**Exit criteria:** All steps 0.1–0.6 pass; three baseline artifacts saved under `runs/baseline/`.

---

#### 0.1 Environment setup

| Step | Command | Pass if |
|------|---------|---------|
| Clone / enter repo | `cd RepoPilot-SWE-Multi-agent` | In project root |
| Create venv | `python3 -m venv venv && source venv/bin/activate` | Prompt shows `(venv)` |
| Editable install | `pip install -e '.[dev]'` | No errors |
| Verify import | `python -c "import minisweagent; print(minisweagent.__version__)"` | Prints version (e.g. `2.4.2`) |
| Verify CLI | `mini --help` | Shows help text |

> **Tip:** Always use `python -m pytest` (not bare `pytest`) so tests use the same interpreter as `python`.

---

#### 0.2 Model & API config

| Step | Command | Pass if |
|------|---------|---------|
| Set API key | `mini-extra config set OPENAI_API_KEY "sk-..."` | Key saved |
| Set base URL (optional) | `mini-extra config set OPENAI_BASE_URL "https://your-host/v1"` | Only if using proxy |
| Set default model | `mini-extra config set MSWEA_MODEL_NAME "openai/gpt-4o"` | Model name includes provider prefix |
| Verify config file | `mini-extra config edit` or `cat ~/Library/Application\ Support/mini-swe-agent/.env` | Keys present |

Config file location is printed when you run `mini --help`.

---

#### 0.3 Unit smoke tests (no API, free)

Confirms install + agent loop without spending tokens.

```bash
python -m pytest tests/run/test_local.py tests/run/test_run_hello_world.py -v
python -m pytest tests/run/test_sudoku.py -v
bash scripts/repro_sudoku.sh
```

| Pass if |
|---------|
| All listed tests **PASSED** |
| `repro_sudoku.sh` exits 0 |

Optional broader check:

```bash
python -m pytest tests/run/test_cli_integration.py tests/run/test_extra_config.py -v
```

---

#### 0.4 Minimal live API smoke test (~$0.03)

Confirms model + API key + bash execution work end-to-end.

```bash
mini -y --exit-immediately --cost-limit 0.03 \
  -t "Your job is to run \`ls\`, verify that you see files, then quit."
```

Or via pytest fire test (requires `--run-fire`):

```bash
python -m pytest tests/test_fire.py::test_litellm_toolcall -v --run-fire
```

| Pass if |
|---------|
| Exit code 0 |
| Agent runs `ls` and submits |
| Trajectory saved (see 0.5 for path) |

---

#### 0.5 Baseline issue-fix run (main Phase 0 deliverable)

Run upstream `mini` on a **real coding task** in this repo. Use the built-in sudoku module as the target—it already has tests and a repro script.

**Suggested task** (save as `runs/baseline/issue.md`):

```markdown
# Fix sudoku hint bug

The sudoku game in `src/minisweagent/run/sudoku.py` has a bug in the hint logic.
Run `python -m pytest tests/run/test_sudoku.py -v` to see failing tests.

Your job:
1. Read the failing test and the sudoku source code
2. Fix the bug so all sudoku tests pass
3. Run pytest to verify
4. Show `git diff` and submit when done
```

**Run command:**

```bash
mkdir -p runs/baseline

mini -y --exit-immediately --cost-limit 0.50 \
  -o runs/baseline/trajectory.traj.json \
  -t "$(cat runs/baseline/issue.md)"
```

Use a higher `--cost-limit` if the model needs more steps. Adjust `-m` if not using the default model.

**Manually verify the four core capabilities:**

| Capability | How agent demonstrates it | You verify |
|------------|----------------------------|------------|
| **Read** | `cat` / `sed` / editor on source files | In trajectory messages |
| **Edit** | Modifies `sudoku.py` (or related) | `git diff` shows changes |
| **Test** | Runs `pytest tests/run/test_sudoku.py` | In trajectory or `baseline_test.log` |
| **Diff** | Runs `git diff` before submit | Patch captured in 0.6 |

| Pass if |
|---------|
| Agent completes without crash |
| `pytest tests/run/test_sudoku.py` passes after agent run (or agent's last test run passed) |
| `git diff` shows a non-empty patch |

> If sudoku is already fixed in your branch, pick another small bug or temporarily revert a commit to create a known-broken state for the baseline run.

---

#### 0.6 Save baseline artifacts

Collect outputs into `runs/baseline/`:

```bash
mkdir -p runs/baseline

# 1. Patch
git diff > runs/baseline/baseline_patch.diff

# 2. Test log
python -m pytest tests/run/test_sudoku.py -v 2>&1 | tee runs/baseline/baseline_test.log

# 3. Run summary (write manually or from trajectory)
#    Include: date, model name, cost, api_calls, exit_status, task summary
```

**`runs/baseline/baseline_run.md` template:**

```markdown
# Baseline Run — upstream mini-swe-agent

- **Date:**
- **Model:** (from MSWEA_MODEL_NAME or -m flag)
- **Task:** runs/baseline/issue.md
- **Exit status:** (from trajectory info.exit_status)
- **API calls:** (from trajectory info.model_stats.api_calls)
- **Cost:** (from trajectory info.model_stats.instance_cost)
- **Tests passed:** yes / no
- **Patch lines:** (wc -l baseline_patch.diff)
- **Notes:** (anything unexpected)
```

| Deliverable | Path |
|-------------|------|
| Run summary | `runs/baseline/baseline_run.md` |
| Patch | `runs/baseline/baseline_patch.diff` |
| Test log | `runs/baseline/baseline_test.log` |
| Trajectory (optional) | `runs/baseline/trajectory.traj.json` |
| Issue used (optional) | `runs/baseline/issue.md` |

---

#### Phase 0 checklist

```
[ ] 0.1  venv + pip install -e '.[dev]' + import works
[ ] 0.2  API key + model configured in .env
[ ] 0.3  Unit smoke tests pass (test_local, test_sudoku, repro_sudoku.sh)
[ ] 0.4  Minimal API smoke test passes (ls task or fire test)
[ ] 0.5  Baseline issue-fix run completes; read/edit/test/diff verified
[ ] 0.6  baseline_run.md + baseline_patch.diff + baseline_test.log saved
```

**Do not start Phase 1 until all boxes are checked.** Phase 1 will reuse this baseline as the comparison anchor.

---

### Phase 1 — Task schema and benchmark runner

**Goal:** Make tasks reproducible and runnable in batch. **Before writing runner code**, settle repo layout so upstream baseline and RepoPilot extensions don't mix.

**Exit criteria:** Directory structure agreed + task schema defined + `task_001` benchmark runnable via a runner script (even if runner only wraps `mini` subprocess).

---

#### 1.0 Design principles

| Principle | Why |
|-----------|-----|
| **Upstream frozen** | Baseline must always mean the same thing; RepoPilot changes must not leak into baseline runs |
| **Data vs code** | `benchmarks/` = task definitions (YAML + issue); `src/repopilot/` = orchestration code |
| **Runs are outputs** | Everything an agent produces goes under `runs/{task_id}/`, never committed (except examples) |
| **Phase 1 = thin wrapper** | Runner calls upstream `mini` via subprocess; no self-repair / multi-agent yet |

---

#### 1.1 Target project structure (**confirmed**)

Move current `mini-swe-agent` source into `upstream/`. Add new `repopilot` package at repo root.

**Confirmed decisions:**
- `docs/` → `upstream/docs/` (upstream mini-swe-agent docs only; add `docs/repopilot/` at root later if needed)
- `tests/` → split into `upstream/tests/` (all existing mini tests) + `tests/repopilot/` (RepoPilot tests at repo root)

```text
RepoPilot-SWE-Multi-agent/
│
├── upstream/                          # frozen mini-swe-agent (baseline reference)
│   ├── src/minisweagent/
│   ├── tests/                         # ALL current upstream tests (git mv)
│   ├── docs/                          # ALL current upstream docs (git mv)
│   ├── pyproject.toml
│   ├── mkdocs.yml                     # git mv from root
│   ├── README.md                      # upstream README (git mv from root)
│   ├── LICENSE.md                     # git mv from root
│   ├── AGENTS.md                      # upstream agent rules (git mv)
│   └── VERSION                        # pin e.g. 2.4.2
│
├── src/repopilot/                     # NEW: RepoPilot application code
│   ├── __init__.py
│   ├── schema/
│   │   └── task.py
│   ├── runner/
│   │   ├── baseline.py
│   │   └── benchmark.py
│   ├── trace/                         # Layer B — Phase 2 ✅
│   └── eval/                          # Layer C — Phase 2.5 / 4
│       ├── loader.py
│       ├── metrics.py
│       ├── compare.py
│       └── report.py
│
├── benchmarks/
│   ├── README.md
│   └── task_001_sudoku/
│       ├── config.yaml
│       └── issue.md
│
├── runs/
│   ├── baseline/                      # Phase 0 ✅
│   └── task_001_sudoku/
│
├── scripts/
│   ├── extract_baseline.py
│   └── repro_sudoku.sh
│
├── tests/
│   └── repopilot/                     # RepoPilot tests ONLY (new, at repo root)
│       └── test_task_schema.py
│
├── docs/
│   └── repopilot/                     # optional later: RepoPilot-specific docs
│
├── pyproject.toml                     # root: repopilot-swe-agent
├── Plan.md
├── repopilot_swe_agent_mvp_plan.md
└── README.md                          # RepoPilot-facing README (rewrite later)
```

**What NOT to put in `upstream/`:** RepoPilot benchmarks, `runs/`, sudoku bug tasks, `scripts/extract_baseline.py`, Phase 2+ trace/eval code.

**What stays RepoPilot-owned at root:** `benchmarks/`, `runs/`, `src/repopilot/`, `Plan.md`, repopilot tests.

---

#### 1.2 Why `upstream/` (vs keeping `src/minisweagent/` at root)

| Approach | Pros | Cons |
|----------|------|------|
| **A. `upstream/` directory (recommended)** | Clear mental model; baseline = "run upstream mini"; easy to diff against vanilla mini-swe-agent; RepoPilot code can't accidentally patch agent core | One-time migration; two `pyproject.toml` to wire |
| **B. Keep `src/minisweagent/` at root** | Zero migration; `pip install -e .` unchanged | Hard to tell what's upstream vs RepoPilot; baseline drifts as you add features |
| **C. Git submodule to SWE-agent/mini-swe-agent** | Always syncable with official releases | Submodule friction; harder local dev; overkill for MVP |

**Recommendation:** **A** — move via `git mv`, pin version in `upstream/VERSION`, install with:

```bash
pip install -e 'upstream/[dev]'          # provides `mini`, `mini-extra` CLIs
pip install -e '.[dev]'                  # provides `repopilot`, `repopilot-baseline` CLIs
```

Install **upstream first**, then root repopilot package.

---

#### 1.3 Migration plan — `git mv` command list

**Phase 1.1 executes this list.** No feature code until structure verifies.

```bash
# --- 1. Create upstream/ and repopilot skeleton ---
mkdir -p upstream/src
mkdir -p src/repopilot/{schema,runner,trace,eval}
mkdir -p tests/repopilot
touch src/repopilot/__init__.py
touch src/repopilot/runner/__init__.py

# --- 2. Move upstream source ---
git mv src/minisweagent upstream/src/minisweagent

# --- 3. Move ALL upstream tests → upstream/tests/ ---
git mv tests upstream/tests
mkdir tests/repopilot

# --- 4. Move ALL upstream docs → upstream/docs/ ---
git mv docs upstream/docs
mkdir docs/repopilot

# --- 5. Move upstream project files ---
git mv pyproject.toml upstream/pyproject.toml
git mv mkdocs.yml upstream/mkdocs.yml
git mv README.md upstream/README.md
git mv LICENSE.md upstream/LICENSE.md
git mv AGENTS.md upstream/AGENTS.md
git mv CLAUDE.md upstream/CLAUDE.md 2>/dev/null || true
git mv .pre-commit-config.yaml upstream/.pre-commit-config.yaml

# --- 6. Pin upstream version ---
echo "2.4.2" > upstream/VERSION

# --- 7. Write NEW root pyproject.toml (repopilot) — Phase 1.2 ---
# --- 8. Fix upstream/pyproject.toml paths if needed ---

# --- 9. Verify install ---
pip install -e 'upstream/[dev]'
mini --help
python -m pytest upstream/tests/run/test_local.py -v

pip install -e '.[dev]'
python -c "import repopilot"
```

**Path updates after migration:**

| File | Change |
|------|--------|
| `upstream/pyproject.toml` | `where = ["src"]` unchanged |
| `upstream/mkdocs.yml` | Fix relative paths if broken |
| `.github/workflows/*.yaml` | Point pytest at `upstream/tests/` |
| `scripts/repro_sudoku.sh` | Use `pip install -e upstream/` or `PYTHONPATH=upstream/src` |
| `scripts/extract_baseline.py` | Stays at root (RepoPilot tool) |

**What stays at repo root (RepoPilot-owned):**

| Path | Purpose |
|------|---------|
| `benchmarks/` | Task definitions |
| `runs/` | Run outputs |
| `scripts/` | RepoPilot utilities |
| `src/repopilot/` | RepoPilot Python package |
| `tests/repopilot/` | RepoPilot tests only |
| `docs/repopilot/` | RepoPilot docs (later) |
| `Plan.md`, `repopilot_swe_agent_mvp_plan.md` | Planning |
| `pyproject.toml` | RepoPilot package |
| `README.md` | RepoPilot README (rewrite later; `upstream/README.md` = upstream) |

**Tests split rule:**

| Location | Contents |
|----------|----------|
| `upstream/tests/**` | All existing tests today (agents, models, run, sudoku, fire, …) |
| `tests/repopilot/**` | Task schema, runner, trace, eval (new) |

Sudoku test stays in `upstream/tests/run/test_sudoku.py` because `sudoku.py` is upstream code.

---

#### 1.4a Benchmark task design (for evaluation)

Tasks are not just “bugs to fix”—they are **experiments** the harness must explain.

| Tag | Example | Eval use |
|-----|---------|----------|
| `failure_mode: off_by_one` | task_001_sudoku | Test edit-stage accuracy |
| `failure_mode: import_path` | (future) | Test read/search stage |
| `failure_mode: logic` | (future) | Test multi-step reasoning |
| `difficulty: single_file` | task_001 | Baseline sanity |
| `difficulty: multi_file` | (future) | Stress multi-file trace analysis |
| `expected_repair_rounds: 0-1` | task_001 | Control for cost comparison |

Add optional fields to `config.yaml` when needed:

```yaml
eval:
  failure_mode: off_by_one
  difficulty: single_file
  expected_repair_rounds: 1
  tags: [regression, hint-logic]
```

---

#### 1.4 Task config schema (Phase 1.2 deliverable)

Each benchmark task is a directory under `benchmarks/`:

```yaml
# benchmarks/task_001_sudoku/config.yaml
task_id: task_001_sudoku
description: Fix off-by-one bug in sudoku hint()

# Where the agent runs (Phase 1 MVP: this repo itself)
repo:
  path: .                           # local path; or repo_url for clone
  base_commit: "<commit-with-bug>"  # git SHA with planted bug

# Task input
issue_file: issue.md                # relative to task dir

# Verification
test_command: python -m pytest upstream/tests/run/test_sudoku.py -v
expected_behavior: All sudoku tests pass after fix

# Runner settings
agent:
  mode: baseline                      # baseline | repopilot (Phase 6+, optional)
  mini_flags:                         # passed to upstream mini CLI
    - -y
    - --exit-immediately
    - --cost-limit
    - "0.50"
  output_trajectory: runs/{task_id}/trajectory.traj.json
```

**Schema fields (minimum viable):**

| Field | Required | Purpose |
|-------|----------|---------|
| `task_id` | yes | Directory name + run output key |
| `repo.path` or `repo.repo_url` | yes | Where agent executes |
| `repo.base_commit` | yes | Reproducible starting state |
| `issue_file` | yes | Task prompt |
| `test_command` | yes | Post-run verification (runner executes independently too) |
| `expected_behavior` | no | Human-readable success criteria |
| `agent.mode` | yes | `baseline` → upstream mini; later `repopilot` |
| `agent.mini_flags` | no | Extra CLI args |

---

#### 1.5 Benchmark runner design (Phase 1.3–1.4, design only)

Runner flow — **no RepoPilot agent logic yet**, just orchestration:

```text
load benchmarks/task_XXX/config.yaml
  ↓
validate schema
  ↓
prepare workspace
  ├── if repo.path == ".": use cwd
  └── else: clone repo_url to /tmp/...
  ↓
git checkout base_commit          # reproducible buggy state
  ↓
build mini command:
  mini -t "$(cat issue.md)" -o runs/{task_id}/trajectory.traj.json [mini_flags...]
  ↓
subprocess run (cwd = repo)
  ↓
post-run verification:
  run test_command → save runs/{task_id}/verify_test.log
  ↓
collect artifacts:
  trace recorder → trace.json, patch.diff, test.log, final_report.md
  scripts/extract_baseline.py (legacy baseline_* during transition)
  ↓
write runs/{task_id}/run_meta.yaml (task_id, commit, exit code, test pass/fail)
  ↓
git checkout -                    # restore dev branch (optional)
```

**Key design choice:** Runner invokes **`mini` subprocess** (from `upstream/`), not Python import of `DefaultAgent`. Reasons:

- Baseline stays truly upstream
- Same as how users run mini manually (Phase 0 proven path)
- Later RepoPilot mode swaps command to `repopilot run` or similar

---

#### 1.6 First benchmark task: migrate Phase 0 sudoku

Convert Phase 0 ad-hoc setup into `benchmarks/task_001_sudoku/`:

| From (Phase 0) | To (Phase 1) |
|----------------|--------------|
| `runs/baseline/issue.md` | `benchmarks/task_001_sudoku/issue.md` |
| branch `baseline/phase0-sudoku-bug` @ commit | `repo.base_commit` in config.yaml |
| manual `mini` command | runner generates same command |
| `runs/baseline/*` | `runs/task_001_sudoku/*` (Phase 0 baseline/ kept as archive) |

**Important:** Commit the buggy sudoku state so `base_commit` is a real SHA, not a branch name.

---

#### 1.7 Root vs upstream `pyproject.toml` split

**`upstream/pyproject.toml`** — unchanged from current mini-swe-agent:

- `name = "mini-swe-agent"`
- scripts: `mini`, `mini-extra`
- packages: `minisweagent*`

**Root `pyproject.toml`** — new RepoPilot package:

```toml
[project]
name = "repopilot-swe-agent"
dependencies = [
    "mini-swe-agent",   # path: upstream/ via [tool.uv.sources] or pip install -e upstream/
    "pyyaml",
    "pydantic >= 2.0",
    "typer",
]

[project.scripts]
repopilot = "repopilot.runner.benchmark:app"   # Phase 1.4
repopilot-baseline = "repopilot.runner.baseline:app"
```

Install order for dev:

```bash
pip install -e 'upstream/[dev]'
pip install -e '.[dev]'
```

---

#### 1.8 Phase 1 checklist

```
[x] 1.0  Structure decisions locked ✅
[x] 1.1  Execute git mv migration ✅
[x] 1.2  Root pyproject.toml + repopilot skeleton; both packages install ✅
[x] 1.3  Define TaskConfig schema; benchmarks/README.md ✅
[ ] 1.4  benchmarks/task_001_sudoku/ (config.yaml + issue.md + base_commit)
[x] 1.5  Runner subprocess wrapper (baseline mode) ✅
[x] 1.6  repopilot run task_001 → runs/task_001_sudoku/ ✅
[x] 1.7  Verify artifacts match Phase 0 quality ✅
```

**Phase 1 complete.** Layer A (run infrastructure) is done.

---

### Phase 2 — Trace recorder (Layer B)

**Goal:** Every run produces a structured record that eval can parse—turning demos into an analyzable system.

**Status:** v1 implemented; **v2 in progress** (`schema_version: 2.0`, stage labels, failure fields at record time, `failure_reason.md`).

**Tasks (v1 ✅):**
- Parse trajectory → steps, tool calls, pytest runs, patch, metrics
- Write per-run artifacts under `runs/{task_id}/`
- Integrate into runner after each `mini` run

**Tasks (v2 — Phase 3 ✅):**
- Promote `trace.json` to schema **v2** with fields eval needs at **record time** (not only inferred in loader):
  - `outcome`, `failure_category`, `failure_stage`, `failed_step`, `failure_reason` (pytest-grounded summary)
- Per-step **`stage`**: `read` | `edit` | `test` | `submit` | `other` (heuristic from tool/command)
- Per-step **`files_touched`** / edit targets (for multi-file / complex scenarios)
- **`pytest_runs[]`**: pre-fix vs post-fix, exit codes, failing test names when parseable
- Detect **`verify_mismatch`** (agent post-fix pass vs runner verify fail)
- Deprecate duplicate human reports: `final_report.md` = canonical; `baseline_run.md` = legacy alias during transition

**Failure taxonomy** (assign automatically in trace/eval):

| `failure_category` | Detection heuristic |
|------------------|---------------------|
| `tests_never_run` | No pytest in trajectory |
| `tests_still_failing` | Last pytest run exit ≠ 0 |
| `patch_empty` | No patch extracted and no edit command |
| `wrong_file_edited` | Edit command targets file unrelated to failing test (heuristic) |
| `cost_limit_exceeded` | exit_status or trajectory indicates cost stop |
| `agent_exited_early` | Submitted without edit or test |
| `verify_mismatch` | Agent post-fix pytest passed; runner verify failed |
| `format_error` | Agent format/tool-call errors dominated run |
| `unknown` | Fallback |

**Deliverables:**

| File | Purpose |
|------|---------|
| `trace.json` | Structured RunRecord (eval input) |
| `patch.diff` | Best-effort unified diff |
| `test.log` | Pre/post pytest + runner verify |
| `final_report.md` | Human-readable single-run summary |

---

### Phase 2.5 — Eval harness MVP (Layer C, baseline-only)

**Goal:** Prove the harness on real baseline runs. Compare runs across tasks, dates, or (later) agent modes—without requiring self-repair or multi-agent code.

**Tasks:**
- `src/repopilot/eval/` — `loader.py`, `metrics.py`, `report.py`
- CLI: `repopilot eval summary [--runs-dir runs/]`
- Load all `runs/*/trace.json` + `run_meta.yaml`
- Produce `runs/eval/summary/eval_report.md`, `metrics.json`, `failure_breakdown.md`
- Per-task drill-down: `runs/eval/{task_id}/run_summary.md`

**Exit criteria:** Given 1+ completed benchmark runs, one command produces aggregate report with failure breakdown.

**Note:** This phase does **not** require RepoPilot agent mode—baseline-only eval is valid and is the **default path** until Layer E experiments exist.

---

### Phase 3 — Trace v2 & deep failure attribution (Layer B, **Next**)

**Goal:** Make every run a first-class **RunRecord** that eval and visualization can consume without re-parsing raw trajectories. Support **complex code scenarios** (multi-file edits, long trajectories, misleading failures) via richer structure—not multi-agent roles.

**Tasks:**
- Implement `trace.json` schema v2 fields (see Phase 2 v2 list)
- Extend `trace/recorder.py` to classify steps and attach failure fields at write time
- Parse pytest output for **failing test names** and **assertion snippets** where possible
- Emit **`failure_reason.md`** per run: templated, pytest-grounded explanation (optional LLM summary later, never as sole ground truth)
- Add task-level tags from `config.yaml`: `failure_mode`, `difficulty` → copied into trace for eval grouping

**Exit criteria:** Given a failed baseline run on a multi-step task, `trace.json` + `failure_reason.md` answer *where* and *why* without opening `trajectory.traj.json`.

---

### Phase 4 — Eval harness full (Layer C, **Next**)

**Goal:** Primary resume/demo artifact—**quantify and explain** agent behavior across tasks, runs, and (later) modes. Goes beyond Phase 2.5 aggregate counts.

**Prerequisites:** Phase 2.5 MVP ✅ + Phase 3 trace v2 (partial OK) + ≥2 benchmark tasks with runs.

**Components:**

| Module | File | Responsibility |
|--------|------|----------------|
| Loader | `eval/loader.py` ✅ | Discover runs, normalize to RunRecord |
| Metrics | `eval/metrics.py` ✅ | Aggregate success, cost, rounds, failure breakdown |
| Compare | `eval/compare.py` 🔲 | Pair runs per `task_id` (same task, different dates/modes); Δ success/cost/steps |
| Failure analysis | `eval/failure_analysis.py` 🔲 | Taxonomy counts + **exemplar runs** + per-`failure_mode` breakdown |
| Report | `eval/report.py` ✅ → extend | Render markdown + CSV + per-task side-by-side |

**CLI:**

```bash
repopilot eval summary                         # aggregate (✅)
repopilot eval compare --task task_001         # drill-down across runs 🔲
repopilot eval breakdown --by failure_mode     # group by task tags 🔲
```

**Deliverables:**

```text
runs/eval/summary/
  eval_report.md
  metrics.json
  comparison_table.csv
  failure_breakdown.md

runs/eval/{task_id}/
  run_summary.md
  trajectory_analysis.md    # step timeline, tool stats, file touch map 🔲
```

**Complex scenario analysis (explicit goals):**
- Compare trajectories on **steps-to-first-edit**, **tests before edit**, **files touched count**
- Surface **wrong_file_edited** and **tests_still_failing** with exemplar snippets from `test.log`
- Group metrics by `failure_mode` / `difficulty` tags on benchmark tasks

---

### Phase 5 — Trajectory visualization (Layer D)

**Goal:** Make trajectories and failures **visible**—not only tabular in markdown.

**Tasks (incremental):**
- **v1 (static):** Mermaid step timelines in `trajectory_analysis.md`; failure distribution charts as ASCII or embedded SVG in eval reports
- **v2 (interactive, post-MVP):** React trace dashboard—step timeline, pytest pre/post panel, patch diff viewer, cost curve
- CLI or script: `repopilot eval view runs/task_001_sudoku` → open HTML report locally

**Exit criteria:** A reviewer can understand a failed run’s story (read → edit → test → fail) without reading raw JSON.

---

## Adhoc workflow (user-reported bugs)

**Parallel track** for real-world input outside the 14-task benchmark suite. Adhoc runs share the same runner, trace v2, and verify pipeline—but **must not** be mixed into benchmark `success_rate` aggregates.

### Adhoc vs benchmark

| Dimension | Benchmark (`task_001`–`014`) | Adhoc |
|-----------|-------------------------------|-------|
| Bug source | `setup.patch` injects a known bug | Code is **already buggy** (no patch) |
| Tests | Pre-existing pytest suite | **May be missing** |
| Success criterion | `test_command` passes (runner verify) | Must define an oracle first (usually repro test) |
| Reproducibility | High (fixed commit + patch) | Lower (user snapshot / HEAD) |
| Eval use | Quantitative compare, success rate | **Case study + trace review**; separate bucket |

**Non-negotiable:** Adhoc remains **execution-grounded**. Runner independent verify is required. Without an executable oracle (pytest, repro script, or smoke command), there is no formal `tests_passed` and the run is demo-only—not eval-grade.

**Ideal end-to-end flow:**

```text
User input: repo path + issue (symptom description) + optional snippet
    ↓
[1] Snapshot into git worktree (no setup.patch; base_commit = HEAD or user SHA)
    ↓
[2] (Optional) Agent writes tests/test_repro.py or scripts/repro.sh
    ↓
[3] mini fixes code (baseline single-pass; Phase D adds multi-round repair)
    ↓
[4] Runner runs test_command independently (includes any new tests)
    ↓
[5] trace + eval (tags: adhoc, tests_preexisting | tests_generated; separate bucket)
```

**Already supported today:** optional `setup_patch`; `TaskConfig` + worktree + verify + trace v2; `expected_behavior` (documentation only).

**Gaps:** `repo_url` clone (`NotImplementedError` in runner); adhoc CLI; task/issue templates; eval tags for oracle source; eval bucket separation; repilot mode for “write test then fix.”

---

### Adhoc Phase A — Manual demo (no code changes)

**Goal:** One or two polished demo cases that prove the product narrative—**after** benchmark eval (001–014) is stable.

**When:** Immediately after `feature/eval` merges; no harness PR required.

**Tasks:**
- [x] Define adhoc task layout: `benchmarks/adhoc_<name>/` (excluded from formal benchmark list)
- [x] Author `config.yaml` template: no `setup_patch`, `base_commit: HEAD`, `test_command` pointing at repro tests
- [x] Author `issue.md` template: symptom + explicit instructions (“write minimal repro test if missing, fix bug, run pytest, submit diff”)
- [x] Human or agent pre-writes `tests/test_repro.py` (1–3 cases) → `repopilot run adhoc_<name>`
- [x] Store outputs under `runs/adhoc_<name>/` or tag runs so `eval summary` excludes them from benchmark totals

**Exit criteria:** One complete trace (issue → repro test → fix → runner verify) suitable for demo / interview walkthrough.

**Explicitly not doing:** repilot mode, `repo_url` clone, automatic test generation, mixing adhoc into benchmark success rate.

---

### Adhoc Phase B — Harness extensions (small PR)

**Goal:** Make adhoc tasks first-class in docs and eval tagging—still **baseline `mini`**, no new agent logic.

**Tasks:**
- [ ] Add `benchmarks/_template_adhoc/` + section in `benchmarks/README.md`
- [ ] Extend `EvalTags`: document tags `adhoc`, `tests_preexisting`, `tests_generated`; optional `verify_tier: strict | smoke`
- [ ] Record tags in `trace.json` → `task_tags`; note in patch metadata if new test files were added
- [ ] Eval filtering: `repopilot eval summary --benchmark-only` (or exclude runs tagged `adhoc` by default)
- [ ] Separate adhoc section in `failure_breakdown.md` when adhoc runs are present
- [ ] Document weak-verify conventions (smoke / `py_compile`) and mark `verify_tier: smoke` in trace

**Exit criteria:** An adhoc task can be run, traced, and summarized without polluting benchmark metrics.

**Not in scope:** `--adhoc` CLI, `repo_url` clone, agent-authored test workflow.

---

### Adhoc Phase C — User repo integration (medium PR)

**Goal:** Accept arbitrary local or remote repos without hand-crafting a benchmark directory each time.

**Tasks:**
- [ ] Implement `repo_url` clone in `resolve_repo_path` → cache under `runs/.cache/repos/`
- [ ] CLI: `repopilot run --adhoc <repo_path|url> <issue.md> [--commit SHA] [--test-cmd ...]`
  - Generates ephemeral task config + output dir `runs/adhoc_<timestamp>/`
- [ ] Optional: non-git directories → copy tree, `git init`, initial commit, then worktree
- [ ] Default output isolation: adhoc under `runs/adhoc/`; benchmark eval excludes by path or tag

**Exit criteria:** User can point at a repo + issue file and get full trace + verify without editing `benchmarks/`.

**Depends on:** Adhoc Phase B (tagging and eval separation).

---

### Adhoc Phase D — Agent workflow (Layer E; ties to Phase 6)

**Goal:** “Write repro test → fix bug → runner verify” as a measurable workflow—**separate metrics** from benchmark oracle tasks.

**When:** After benchmark report is stable and at least one Adhoc Phase A demo exists. Overlaps Phase 6 (self-repair) and optionally Phase 7 (roles).

**Tasks:**
- [ ] `agent.mode: repopilot` (or prompt protocol): Stage 1 write repro; Stage 2 fix code (same trajectory)
- [ ] Trace fields: `tests_authored_by: agent | user | preexisting`
- [ ] Metrics: repro fails on buggy state; passes after fix; no unrelated regressions
- [ ] Self-repair loop on verify failure (reuse Phase 6 repair rounds)
- [ ] Failure taxonomy extensions: `tests_never_written`, `repro_does_not_fail`, `fix_breaks_repro`
- [ ] One or two **frozen** adhoc cases (fixed repo snapshot + issue) for repeat runs—still excluded from benchmark success rate

**Exit criteria:** Adhoc run where agent authors the oracle, runner verify passes, and eval reports adhoc bucket separately with test-generation quality signals.

**Sequencing:** Optional; do not block benchmark harness or Phase 5 visualization.

---

### Adhoc eval policy

| Scenario | Include in benchmark `success_rate`? | How to use |
|----------|--------------------------------------|------------|
| `task_001`–`014` | Yes | Primary quantitative eval |
| Adhoc, no verify oracle | No | Trajectory demo only; no formal outcome |
| Adhoc + smoke verify | No (separate bucket) | Tag `verify_tier: smoke`; case study only |
| Adhoc + agent-written pytest + runner verify | No (separate bucket) | Tag `tests_generated`; trace + optional adhoc report |

**Principles:**
- Never merge adhoc and benchmark into one success-rate table.
- Adhoc value is **real input + establish oracle + same trace/verify pipeline**—not “fix without tests.”
- Product narrative: benchmark = quantify; adhoc = real-world story; both share harness artifacts.

**Recommended sequencing:**

```text
Now (post feature/eval)
  └─ Adhoc Phase A: one manual demo

Next small PR
  └─ Adhoc Phase B: template + eval tags + benchmark-only filter

When user-repo onboarding is needed
  └─ Adhoc Phase C: --adhoc CLI + repo_url

When demo needs “agent writes tests”
  └─ Adhoc Phase D (+ Phase 6 self-repair if multi-round)
```

---

### Phase 6 — Test-driven self-repair (Layer E, **optional / deferred**)

**Goal:** Use pytest failures to drive patch iteration—**only if** we need multi-round trajectories for harness experiments or Δ-success studies.

**Not required for:** trace depth, eval aggregation, failure attribution, or visualization on baseline `mini` runs.

**Related:** Adhoc Phase D uses the same repair loop for user-reported bugs where the agent may author repro tests first (see [Adhoc workflow](#adhoc-workflow-user-reported-bugs)).

**Tasks:**
- After patch apply, run pytest
- On failure: summarize logs → feed back to agent → regenerate patch
- Cap at 3 repair rounds; stop early on test pass
- Emit per-round artifacts: `repair_round_N.patch`, `repair_round_N_test.log`
- Updated `trace.json` with `repair_rounds[]` timeline

**Repair evaluation protocol** (run via Layer C when/if implemented):

```text
For each task_id:
  Run A: agent.mode = baseline     (upstream mini)
  Run B: agent.mode = repopilot    (self-repair enabled)
  Same: base_commit, model, cost_limit, test_command, issue

Report:
  Δ success rate
  Δ avg cost
  Δ cost per additional success
  repair_effectiveness = P(pass after round N | fail after round N-1)
```

**Loop (reference):**

```python
for round_id in range(3):
    patch = agent(issue, context, previous_failure)
    apply_patch(patch)
    result = run_tests()
    record_repair_round(round_id, patch, result)   # → trace
    if result.passed:
        break
    previous_failure = summarize_failure(result.logs)
```

---

### Phase 7 — Agent roles (Layer E, **optional / eval-gated**)

**Goal:** Controlled role separation—**only where Phase 4 eval shows a specific stage bottleneck** (e.g. high `failure_stage: read` or `wrong_file_edited` rate).

**Not an MVP requirement.** Default agent remains upstream `mini` in baseline mode.

**Tasks (if justified by data):**
- **Planner:** parse issue → modification plan + search keywords
- **Coder:** generate patch from context
- **Tester:** run tests + parse/attribute failure logs
- **Reviewer:** flag risky diffs (hardcoding, test-only changes, oversized patches)

**Deliverables:**
- `agents/planner.py`, `coder.py`, `tester.py`, `reviewer.py` (only if built)
- Eval comparison: roles-on vs roles-off (same harness protocol as Phase 6)

**Sequencing note:** Skip entirely if baseline trace + eval already explain failures well enough for the thesis/demo.

---

### Phase 8 — Post-MVP enhancements

Only after Phases 3–5 (trace v2, eval full, visualization v1) are solid:

- Docker sandbox (highest priority—execution safety)
- Tree-sitter symbol retrieval
- Interactive React trace dashboard (extends Phase 5 v2)
- GitHub PR summary
- Multi-language support
- `repopilot eval batch` — run all benchmarks + eval in one command

---

## Success Criteria

MVP is **done** when all of the following are true (eval-harness-centric; **no self-repair or role split required**):

1. Runs **5–10** benchmark tasks end-to-end in **baseline** mode (upstream `mini`)
2. Produces **`trace.json` v2** + **`patch.diff`** + runner-verified test result per run
3. **Actually runs pytest** via runner verify (not mocked, not agent-only)
4. Eval harness produces **`eval_report.md`**, **`metrics.json`**, **`failure_breakdown.md`**
5. For **every failed run**, harness outputs `failure_category`, `failure_stage`, `failed_step`, and pytest-grounded **failure reason**
6. **Trajectory analysis** available per task: step timeline, tool/test stats, files touched (markdown minimum; visualization Phase 5)
7. Eval supports **grouping/breakdown** by task tags (`failure_mode`, `difficulty`) and **compare** across runs on the same task
8. Dev checkout **unchanged** after benchmark runs (git worktree isolation)
9. README includes **eval-centric architecture diagram**, **demo walkthrough**, and example eval report

**Optional stretch (Layer E):** self-repair or role experiments with Δ success vs baseline documented in eval compare—not a blocker for MVP.

---

## Current status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 0 | **Done** | baseline trajectory + extracted artifacts in `runs/baseline/` |
| Phase 1 | **Done** | Task schema, runner, task_001 end-to-end ✅ |
| Phase 2 | **Done (v1)** | Trace recorder; v2 → Phase 3 |
| Phase 2.5 | **Done** | Eval harness MVP (`repopilot eval summary`) |
| Phase 3 | **Done** | Trace v2 + failure_reason at record time |
| Phase 4 | **Done** | Eval compare, breakdown, failure exemplars |
| Phase 5 | **Done** | Trajectory visualization (Mermaid, ASCII, `eval view`) |
| Adhoc A | **Done** | Demo `adhoc_parser_empty` + `_template_adhoc`; see benchmarks/adhoc_parser_empty/README.md |
| Adhoc B | Not started | Template + eval tags + benchmark-only filter |
| Adhoc C | Not started | `--adhoc` CLI + `repo_url` clone |
| Adhoc D | Deferred | Agent writes repro + fix; ties to Phase 6 |
| Phase 6 | Deferred | Self-repair (optional Layer E) |
| Phase 7 | Optional | Agent roles (eval-gated only) |
| Phase 8 | Post-MVP | Docker, batch eval, … |

| Layer | Status |
|-------|--------|
| A. Run infrastructure | ✅ (incl. git worktree isolation) |
| B. Observable run record | ✅ v2 |
| C. Evaluation harness | ✅ full (compare, breakdown, exemplars) |
| D. Visualization | ✅ |
| E. Agent experiments | 🔲 deferred |
| **Adhoc (parallel)** | 🔲 A → B → C → D |

**Recommended next steps:** Merge `feature/eval` → Adhoc Phase A (one demo case) → Adhoc Phase B (harness tags) → Phase 6 self-repair (optional) / Adhoc Phase D.

---

## Key principles

1. **Eval-first** — trace schema and metrics design drive agent features, not the reverse.
2. **Harness before agents** — deepen analyze / quantify / visualize on baseline `mini` before building self-repair or role splits.
3. **Test results over LLM self-assessment** — correctness is grounded in runner verify + pytest output.
4. **Explain failures, not just count them** — every failed run gets category, stage, step, and pytest-grounded reason.
5. **Trace everything** — every run must be debuggable and comparable via `trace.json`.
6. **Baseline first, fair compare** — same task, commit, model, cost limit when comparing runs or modes.
7. **Scope discipline** — Python + pytest + local repo until eval MVP ships.
8. **Agent features must earn their cost** — self-repair and roles need Δ success in eval report, or they stay deferred.

---

## References

- Source plan: [repopilot_swe_agent_mvp_plan.md](repopilot_swe_agent_mvp_plan.md)
- Upstream: [mini-swe-agent docs](https://mini-swe-agent.com/latest/)
- Local quickstart: [docs/quickstart.md](docs/quickstart.md)
