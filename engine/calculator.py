"""
Version router and result tagger for the metric calculation engine.
"""

import csv
from datetime import date, datetime, timezone
from pathlib import Path

from .definitions import REGISTRY, SUMMARIES

DATA_PATH = Path(__file__).parent.parent / "data" / "canonical.csv"


def load_canonical(path: Path = DATA_PATH) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def calculate(
    version: str,
    period_start: date,
    period_end: date,
    rows: list[dict] | None = None,
) -> dict:
    if version not in REGISTRY:
        raise ValueError(f"Unknown version '{version}'. Available: {list(REGISTRY)}")

    if rows is None:
        rows = load_canonical()

    fn = REGISTRY[version]
    result = fn(rows, period_start, period_end)

    result["computed_at"] = datetime.now(timezone.utc).isoformat()
    result["definition_summary"] = SUMMARIES[version]
    result["row_count_used"] = len(rows)
    return result
