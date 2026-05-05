# engine/CLAUDE.md

## Module Purpose
Versioned metric calculation engine. Every result is tagged with the definition version that produced it.

## Stack
- Python + FastAPI (`uvicorn engine.app:app --reload --port 8002`)
- No database — reads from `data/canonical.csv`
- Tests: `pytest engine/tests/`

## Adding a New Definition Version
1. Create `engine/definitions/vN.py` — implement `calculate(rows, period_start, period_end) -> dict`
2. Register in `engine/definitions/__init__.py` (REGISTRY + SUMMARIES)
3. Add a test file `engine/tests/test_vN.py` covering normal, boundary, and exclusion cases
4. Add a row to `decisions/metric-definition.md` version history
5. Add a column to `evals/reconciliation.md`

## Result Shape Contract
Every `calculate()` must return:
```python
{
  "version": "vN",
  "label": str,
  "numerator": float | int,
  "denominator": float | int,
  "value": float | None,   # None if denominator == 0
  "period_start": str,     # ISO date
  "period_end": str,       # ISO date
  "parameters": dict,      # all thresholds, explicit
}
```
`computed_at` and `definition_summary` are added by `calculator.py` — do not add them in definition files.

## Boundaries
- Definition files must NOT read files or call external services.
- All thresholds must be named constants at the top of each definition file, not magic numbers.
- The engine does NOT redact PII — that is the `PostToolUse` hook's responsibility.
