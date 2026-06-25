# Adhoc — coach-agent duplicate chat routes (ISSUE-001)

**Phase C** adhoc task against an **external** repository. Not part of the formal `task_001`–`task_014` benchmark suite.

**Coach-agent has no pytest suite.** Runner verify uses a **smoke static check** (duplicate route count in `main.py`), not full auth tests.

| File | Purpose |
|------|---------|
| `issue.md` | Bug report passed to mini — still asks agent to add 401 tests if it can |
| `config.yaml` | Repo URL, commit, smoke `test_command` |
| `README.md` | This file |

## Bug summary

- **Location:** `backend/app/api/main.py` (duplicate routes L238–300 vs L302–328)
- **Expected fix:** Remove duplicates L302–328; JWT on remaining handlers

Details: [`issue.md`](issue.md)

## Verify strategy (no tests in repo)

| Layer | What it checks |
|-------|----------------|
| **Runner verify** (`test_command`) | Each of `/v1/chat/sessions/{user_id}` and `/v1/chat/history/{session_id}` appears **exactly once** in `main.py` |
| **Agent (mini)** | May add pytest or manual checks during the run — see `trajectory.traj.json` |
| **You (manual)** | Review `patch.diff`: JWT on routes, no dead unauthenticated handlers |

Smoke verify **does not** prove unauthorized requests return 401. After the run, inspect the patch or hit the API locally.

### `--skip-mini` before agent

```bash
repopilot run adhoc_coach_agent --skip-mini
# expect verify FAIL: "sessions route defined 2 times"
```

### After agent

```bash
repopilot run adhoc_coach_agent
# expect verify PASS if duplicate routes removed
# then read patch.diff for JWT / test additions
```

## Run

```bash
repopilot run adhoc_coach_agent --dry-run    # clone + print commands
repopilot run adhoc_coach_agent --skip-mini
repopilot run adhoc_coach_agent
repopilot eval view adhoc_coach_agent --open
```

Ephemeral CLI equivalent:

```bash
repopilot adhoc run https://github.com/zhe0328/coach-agent.git \
  benchmarks/adhoc_coach_agent/issue.md \
  --test-cmd 'cd backend && python -c "from pathlib import Path; t=Path('"'"'app/api/main.py'"'"').read_text(); assert t.count('"'"'\"/v1/chat/sessions/{user_id}\"'"'"')==1; assert t.count('"'"'\"/v1/chat/history/{session_id}\"'"'"')==1"' \
  --verify-tier smoke \
  --commit master
```

First run clones to `runs/.cache/repos/`. Artifacts: `runs/adhoc_coach_agent/`.

## Where the fix ends up

```bash
cat runs/adhoc_coach_agent/patch.diff
cd /path/to/coach-agent && git apply /path/to/RepoPilot/runs/adhoc_coach_agent/patch.diff
```

Not pushed to GitHub automatically.

## Later: add real pytest

When coach-agent has auth tests, switch `config.yaml`:

```yaml
eval:
  verify_tier: strict
  tags: [adhoc, tests_preexisting]
test_command: cd backend && pytest tests/test_chat_auth.py -v
```

## Checklist

- [x] `repo_url` / `base_commit` set
- [x] Smoke verify (no pytest required)
- [ ] `--skip-mini` fails on buggy `master` (duplicate routes)
- [ ] Full run → `patch.diff` removes L302–328
- [ ] Manual review: JWT + optional agent-written tests
