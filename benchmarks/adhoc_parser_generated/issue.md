# Empty CSV input raises instead of returning empty list

A user reported that our comma-separated parser crashes when given an empty string.

## Symptom

Calling `parse_items("")` raises `ValueError: empty input`. Product spec says empty input should return `[]`.

## Code location

- Implementation: `benchmarks/adhoc_parser_generated/fixture/list_parser.py`

## Important: no reproduction tests yet

QA has **not** written pytest for this report. You must **author** the repro tests yourself before fixing the bug.

## Your job

1. Reproduce the bug manually (e.g. run Python with `from list_parser import parse_items` and call `parse_items("")`).
2. **Create** `benchmarks/adhoc_parser_generated/fixture/tests/test_repro.py` with pytest cases that **fail** on the current code. Include at least:
   - empty string `""` → `[]` (must not raise)
   - one non-empty case (e.g. single item or comma-separated values)
3. Fix `list_parser.py` so your tests pass.
4. Run pytest again to confirm.
5. Run `git diff` and submit when done.

After you create the test file, verify with:

```bash
PYTHONPATH=benchmarks/adhoc_parser_generated/fixture \
  python -m pytest benchmarks/adhoc_parser_generated/fixture/tests/test_repro.py -v
```
