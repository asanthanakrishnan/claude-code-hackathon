"""
Data pipeline: dedup, timezone reconcile, gap detection → canonical.csv

Run: python data/pipeline.py
Output: data/canonical.csv + data/pipeline_report.json
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCES = ["source_a.csv", "source_b.csv", "source_c.csv", "source_d.csv"]
SOURCE_TIMEZONES = {
    "source_a.csv": ZoneInfo("America/New_York"),  # UTC-5, dates recorded in local time
}

FIELDNAMES = [
    "subscription_id", "customer_id", "customer_name", "customer_email",
    "plan", "region", "mrr", "subscription_start", "subscription_end",
    "status", "churned_at", "downgraded_from_mrr", "expanded_to_mrr",
    "recorded_at", "source_file", "data_quality_flags",
]

ROOT = Path(__file__).parent


def load_source(filename: str) -> list[dict]:
    path = ROOT / filename
    if not path.exists():
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def normalize_timestamp(ts: str, source: str) -> str:
    """Convert source-local timestamp to UTC ISO string."""
    if not ts:
        return ts
    try:
        dt = datetime.fromisoformat(ts)
        tz = SOURCE_TIMEZONES.get(source)
        if tz and dt.tzinfo is None:
            # Source A: recorded in NYC local time but missing tz info
            dt = dt.replace(tzinfo=tz)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return ts


def validate_row(row: dict) -> list[str]:
    """Return list of data quality flags for a row."""
    flags = []
    if not row.get("mrr"):
        flags.append("missing_mrr")
    else:
        try:
            if float(row["mrr"]) <= 0:
                flags.append("invalid_mrr")
        except ValueError:
            flags.append("invalid_mrr")

    if not row.get("subscription_end"):
        flags.append("missing_subscription_end")

    if not row.get("status"):
        flags.append("missing_status")

    valid_statuses = {"active", "churned", "downgraded", "expanded"}
    if row.get("status") and row["status"] not in valid_statuses:
        flags.append(f"unknown_status:{row['status']}")

    # Churned rows must have churned_at
    if row.get("status") == "churned" and not row.get("churned_at"):
        flags.append("churned_missing_date")

    return flags


def dedup(rows: list[dict]) -> tuple[list[dict], int]:
    """Last-write-wins by subscription_id, sorted by recorded_at ascending."""
    seen: dict[str, dict] = {}
    dupe_count = 0
    sorted_rows = sorted(
        rows,
        key=lambda r: r.get("recorded_at") or "",
    )
    for row in sorted_rows:
        sid = row.get("subscription_id", "")
        if sid in seen:
            dupe_count += 1
        seen[sid] = row
    return list(seen.values()), dupe_count


def run_pipeline() -> dict:
    all_rows: list[dict] = []

    for source in SOURCES:
        raw = load_source(source)
        for row in raw:
            row["recorded_at"] = normalize_timestamp(row.get("recorded_at", ""), source)
            row["source_file"] = source
        all_rows.extend(raw)

    # Dedup across all sources
    deduped, dupe_count = dedup(all_rows)

    # Validate and flag
    canonical = []
    quality_summary = {
        "total_input": len(all_rows),
        "duplicates_removed": dupe_count,
        "rows_with_flags": 0,
        "flag_counts": {},
    }

    for row in deduped:
        flags = validate_row(row)
        row["data_quality_flags"] = "|".join(flags) if flags else ""
        if flags:
            quality_summary["rows_with_flags"] += 1
            for f in flags:
                quality_summary["flag_counts"][f] = quality_summary["flag_counts"].get(f, 0) + 1
        canonical.append(row)

    quality_summary["total_canonical"] = len(canonical)

    # Write canonical
    out_path = ROOT / "canonical.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(canonical)

    # Write pipeline report
    report_path = ROOT / "pipeline_report.json"
    with open(report_path, "w") as f:
        json.dump(quality_summary, f, indent=2)

    print(f"Pipeline complete:")
    print(f"  Input rows:          {quality_summary['total_input']}")
    print(f"  Duplicates removed:  {dupe_count}")
    print(f"  Canonical rows:      {len(canonical)}")
    print(f"  Rows with flags:     {quality_summary['rows_with_flags']}")
    print(f"  Flags: {quality_summary['flag_counts']}")

    return quality_summary


if __name__ == "__main__":
    run_pipeline()
