# User-reported bug title

Describe the symptom in plain language (what the user sees, not root cause).

## Symptom

…

## Code location

- Implementation: `benchmarks/adhoc_EXAMPLE/fixture/...`
- Reproduction tests: `benchmarks/adhoc_EXAMPLE/fixture/tests/test_repro.py`

If tests do not exist yet, write them first (1–3 minimal cases), then fix the bug.

## Your job

1. Run the reproduction tests — at least one should fail on the current code
2. Read the implementation and fix the bug
3. Run pytest again to verify all tests pass
4. Run `git diff` and submit when done

```bash
PYTHONPATH=benchmarks/adhoc_EXAMPLE/fixture \
  python -m pytest benchmarks/adhoc_EXAMPLE/fixture/tests/test_repro.py -v
```
