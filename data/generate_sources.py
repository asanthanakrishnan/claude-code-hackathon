"""
Generates four noisy subscription CSV files — each with a distinct data quality problem.
Simulates the "The Mess" layer from architecture.md.

Domain: SaaS Monthly Churn Rate
Schema: subscription_id, customer_id, customer_name, customer_email, plan,
        region, mrr, subscription_start, subscription_end, status,
        churned_at, downgraded_from_mrr, expanded_to_mrr, recorded_at
"""

import csv
import random
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

random.seed(42)

PLANS = {"starter": 99, "growth": 399, "enterprise": 1499}
REGIONS = ["us-east", "us-west", "eu", "apac"]
STATUSES = ["active", "churned", "downgraded", "expanded"]

FIRST_NAMES = ["Alex", "Jordan", "Morgan", "Taylor", "Casey", "Riley", "Quinn", "Dana"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
DOMAINS = ["acme.com", "globex.io", "initech.net", "umbrella.co", "cyberdyne.tech"]


def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def random_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def random_email(name: str, domain: str) -> str:
    parts = name.lower().split()
    return f"{parts[0]}.{parts[1]}@{domain}"


def generate_subscriptions(n: int = 200) -> list[dict]:
    subs = []
    base_start = date(2024, 1, 1)
    base_end = date(2024, 10, 31)

    for _ in range(n):
        plan = random.choice(list(PLANS))
        mrr = PLANS[plan] + random.randint(-10, 10)
        start = random_date(base_start, base_end)
        end = start + timedelta(days=random.randint(28, 365))
        name = random_name()
        domain = random.choice(DOMAINS)
        email = random_email(name, domain)

        status_weights = [0.55, 0.25, 0.12, 0.08]
        status = random.choices(STATUSES, weights=status_weights)[0]

        churned_at = None
        downgraded_from_mrr = None
        expanded_to_mrr = None

        if status == "churned":
            # Churn happens 0-45 days after subscription_end
            days_after = random.randint(0, 45)
            churned_at = end + timedelta(days=days_after)
        elif status == "downgraded":
            downgraded_from_mrr = mrr
            mrr = max(50, mrr - random.choice([100, 200, 400, 1100]))
        elif status == "expanded":
            expanded_to_mrr = mrr + random.choice([100, 300, 500])

        subs.append({
            "subscription_id": str(uuid.uuid4())[:8],
            "customer_id": str(uuid.uuid4())[:8],
            "customer_name": name,
            "customer_email": email,
            "plan": plan,
            "region": random.choice(REGIONS),
            "mrr": mrr,
            "subscription_start": start.isoformat(),
            "subscription_end": end.isoformat(),
            "status": status,
            "churned_at": churned_at.isoformat() if churned_at else "",
            "downgraded_from_mrr": downgraded_from_mrr if downgraded_from_mrr else "",
            "expanded_to_mrr": expanded_to_mrr if expanded_to_mrr else "",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })
    return subs


FIELDNAMES = [
    "subscription_id", "customer_id", "customer_name", "customer_email",
    "plan", "region", "mrr", "subscription_start", "subscription_end",
    "status", "churned_at", "downgraded_from_mrr", "expanded_to_mrr", "recorded_at",
]


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def make_source_a(subs: list[dict]) -> list[dict]:
    """Source A: timestamps are in America/New_York (UTC-5) instead of UTC."""
    ny = ZoneInfo("America/New_York")
    rows = []
    for s in subs[:100]:
        row = dict(s)
        # Shift recorded_at to NYC local time without tz info — looks like UTC
        local_dt = datetime.fromisoformat(s["recorded_at"]).astimezone(ny)
        row["recorded_at"] = local_dt.replace(tzinfo=None).isoformat()
        rows.append(row)
    return rows


def make_source_b(subs: list[dict]) -> list[dict]:
    """Source B: ~15% of records are duplicated from a retry storm."""
    rows = list(subs[80:180])
    dupe_indices = random.sample(range(len(rows)), k=int(len(rows) * 0.15))
    dupes = [dict(rows[i]) for i in dupe_indices]
    rows.extend(dupes)
    random.shuffle(rows)
    return rows


def make_source_c(subs: list[dict]) -> list[dict]:
    """Source C: ~20% of churned/downgraded labels are swapped."""
    rows = []
    for s in subs[50:160]:
        row = dict(s)
        if row["status"] == "churned" and random.random() < 0.20:
            row["status"] = "downgraded"
            row["downgraded_from_mrr"] = row["mrr"]
        elif row["status"] == "downgraded" and random.random() < 0.20:
            row["status"] = "churned"
            if not row["churned_at"]:
                end = date.fromisoformat(row["subscription_end"])
                row["churned_at"] = (end + timedelta(days=random.randint(0, 30))).isoformat()
        rows.append(row)
    return rows


def make_source_d(subs: list[dict]) -> list[dict]:
    """Source D: ~25% of rows have nulls in mrr, subscription_end, or status."""
    rows = []
    for s in subs[100:200]:
        row = dict(s)
        if random.random() < 0.25:
            field = random.choice(["mrr", "subscription_end", "status"])
            row[field] = ""
        rows.append(row)
    return rows


def main() -> None:
    out = Path(__file__).parent
    subs = generate_subscriptions(200)

    write_csv(out / "source_a.csv", make_source_a(subs))
    write_csv(out / "source_b.csv", make_source_b(subs))
    write_csv(out / "source_c.csv", make_source_c(subs))
    write_csv(out / "source_d.csv", make_source_d(subs))

    print(f"Generated source_a ({len(make_source_a(subs))} rows)")
    print(f"Generated source_b ({len(make_source_b(subs))} rows)")
    print(f"Generated source_c ({len(make_source_c(subs))} rows)")
    print(f"Generated source_d ({len(make_source_d(subs))} rows)")


if __name__ == "__main__":
    main()
