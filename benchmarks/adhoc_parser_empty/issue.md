# Empty CSV input raises instead of returning empty list

A user reported that our comma-separated parser crashes when given an empty string.

## Symptom

Calling `parse_items("")` raises `ValueError: empty input`. Product spec says empty input should return `[]`.

## Code location

- Implementation: `benchmarks/adhoc_parser_empty/fixture/list_parser.py`
- Reproduction tests (already written by QA): `benchmarks/adhoc_parser_empty/fixture/tests/test_repro.py`

## Your job

1. Run the reproduction tests — at least one should fail on the current code
2. Read the implementation and fix the bug so empty input returns `[]`
3. Run pytest again to verify all tests pass
4. Run `git diff` and submit when done

```bash
PYTHONPATH=benchmarks/adhoc_parser_empty/fixture \
  python -m pytest benchmarks/adhoc_parser_empty/fixture/tests/test_repro.py -v
```
