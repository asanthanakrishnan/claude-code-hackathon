"""
Agentic Variance Panel — "Explain the variance"

When churn moves unexpectedly, spawns three parallel subagents via the Anthropic API:
  - Geography subagent: segments churn by region
  - Product subagent:   segments churn by plan
  - Time subagent:      looks for intra-period timing patterns

Each subagent receives explicit context (they don't inherit coordinator state).
Returns a structured finding: best explanation + losing theories.

Usage:
  python panel/coordinator.py --version v1 --period-a 2024-05-01 2024-05-31 --period-b 2024-06-01 2024-06-30

Requires: ANTHROPIC_API_KEY environment variable
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic

from engine.calculator import calculate, load_canonical

MODEL = "claude-opus-4-7"


def segment_by_region(rows: list[dict], version: str, period_start: date, period_end: date) -> dict:
    """Pre-compute churn broken out by region — passed as context to geography subagent."""
    from engine.definitions import REGISTRY
    fn = REGISTRY[version]
    regions = sorted({r.get("region", "unknown") for r in rows})
    breakdown = {}
    for region in regions:
        region_rows = [r for r in rows if r.get("region") == region]
        result = fn(region_rows, period_start, period_end)
        breakdown[region] = {
            "value": result["value"],
            "numerator": result["numerator"],
            "denominator": result["denominator"],
        }
    return breakdown


def segment_by_plan(rows: list[dict], version: str, period_start: date, period_end: date) -> dict:
    from engine.definitions import REGISTRY
    fn = REGISTRY[version]
    plans = sorted({r.get("plan", "unknown") for r in rows})
    breakdown = {}
    for plan in plans:
        plan_rows = [r for r in rows if r.get("plan") == plan]
        result = fn(plan_rows, period_start, period_end)
        breakdown[plan] = {
            "value": result["value"],
            "numerator": result["numerator"],
            "denominator": result["denominator"],
        }
    return breakdown


async def run_subagent(client: anthropic.AsyncAnthropic, subagent_type: str, context: dict) -> dict:
    """
    Each subagent gets explicit context — they don't inherit coordinator state.
    Returns a structured finding: {explanation, evidence, confidence, segment_data}.
    """
    prompts = {
        "geography": f"""You are the Geography subagent in a churn variance analysis panel.

Your job: identify whether geographic patterns explain the churn movement described below.

Context (passed explicitly — you have no other information):
{json.dumps(context, indent=2)}

Respond with a JSON object only:
{{
  "subagent": "geography",
  "top_finding": "<one sentence>",
  "evidence": "<which regions drove the change and by how much>",
  "confidence": "high|medium|low",
  "segment_data_summary": "<key numbers>",
  "is_likely_primary_cause": true|false
}}""",

        "product": f"""You are the Product subagent in a churn variance analysis panel.

Your job: identify whether plan/product mix patterns explain the churn movement described below.

Context (passed explicitly — you have no other information):
{json.dumps(context, indent=2)}

Respond with a JSON object only:
{{
  "subagent": "product",
  "top_finding": "<one sentence>",
  "evidence": "<which plans drove the change and by how much>",
  "confidence": "high|medium|low",
  "segment_data_summary": "<key numbers>",
  "is_likely_primary_cause": true|false
}}""",

        "time": f"""You are the Time subagent in a churn variance analysis panel.

Your job: identify whether timing patterns (month-of-year, end-of-quarter, billing cycle artifacts)
explain the churn movement described below.

Context (passed explicitly — you have no other information):
{json.dumps(context, indent=2)}

Respond with a JSON object only:
{{
  "subagent": "time",
  "top_finding": "<one sentence>",
  "evidence": "<what timing patterns you observe>",
  "confidence": "high|medium|low",
  "segment_data_summary": "<key observations>",
  "is_likely_primary_cause": true|false
}}""",
    }

    prompt = prompts[subagent_type]
    response = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"subagent": subagent_type, "top_finding": text, "confidence": "low", "parse_error": True}


async def run_panel(version: str, period_a_start: date, period_a_end: date,
                    period_b_start: date, period_b_end: date) -> dict:
    rows = load_canonical()

    result_a = calculate(version, period_a_start, period_a_end, rows)
    result_b = calculate(version, period_b_start, period_b_end, rows)

    delta = None
    if result_a["value"] is not None and result_b["value"] is not None:
        delta = round(result_b["value"] - result_a["value"], 6)

    if delta is None:
        return {"error": "One or both periods returned no data. Cannot explain variance."}

    direction = "increased" if delta > 0 else "decreased"
    print(f"\nChurn {direction} by {abs(delta):.4%} from period A to period B.")
    print(f"  Period A ({period_a_start}–{period_a_end}): {result_a['value']:.4%}")
    print(f"  Period B ({period_b_start}–{period_b_end}): {result_b['value']:.4%}")
    print("\nSpinning up subagents…")

    # Pre-compute segment breakdowns to pass as explicit context
    geo_a = segment_by_region(rows, version, period_a_start, period_a_end)
    geo_b = segment_by_region(rows, version, period_b_start, period_b_end)
    plan_a = segment_by_plan(rows, version, period_a_start, period_a_end)
    plan_b = segment_by_plan(rows, version, period_b_start, period_b_end)

    base_context = {
        "version": version,
        "definition_summary": result_a["definition_summary"],
        "period_a": {"start": period_a_start.isoformat(), "end": period_a_end.isoformat(), "churn_rate": result_a["value"]},
        "period_b": {"start": period_b_start.isoformat(), "end": period_b_end.isoformat(), "churn_rate": result_b["value"]},
        "delta": delta,
        "direction": direction,
    }

    subagent_contexts = {
        "geography": {**base_context, "region_breakdown_a": geo_a, "region_breakdown_b": geo_b},
        "product": {**base_context, "plan_breakdown_a": plan_a, "plan_breakdown_b": plan_b},
        "time": {
            **base_context,
            "period_a_month": period_a_start.month,
            "period_b_month": period_b_start.month,
            "period_a_quarter": (period_a_start.month - 1) // 3 + 1,
            "period_b_quarter": (period_b_start.month - 1) // 3 + 1,
            "note": "Consider billing cycle artifacts, end-of-quarter effects, seasonal patterns.",
        },
    }

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Warning: ANTHROPIC_API_KEY not set. Returning segment data without LLM analysis.")
        return {
            "version": version,
            "delta": delta,
            "direction": direction,
            "segment_data": subagent_contexts,
            "note": "Set ANTHROPIC_API_KEY to get LLM-synthesized explanations.",
        }

    client = anthropic.AsyncAnthropic(api_key=api_key)

    # Run all three subagents in parallel — each gets explicit context
    findings = await asyncio.gather(
        run_subagent(client, "geography", subagent_contexts["geography"]),
        run_subagent(client, "product", subagent_contexts["product"]),
        run_subagent(client, "time", subagent_contexts["time"]),
    )

    # Coordinator picks the best explanation by confidence + is_likely_primary_cause
    confidence_rank = {"high": 3, "medium": 2, "low": 1}
    primary_candidates = [f for f in findings if f.get("is_likely_primary_cause")]
    if not primary_candidates:
        primary_candidates = findings

    best = max(
        primary_candidates,
        key=lambda f: (
            f.get("is_likely_primary_cause", False),
            confidence_rank.get(f.get("confidence", "low"), 0),
        ),
    )
    losing = [f for f in findings if f is not best]

    return {
        "version": version,
        "period_a": base_context["period_a"],
        "period_b": base_context["period_b"],
        "delta": delta,
        "direction": direction,
        "best_explanation": best,
        "losing_theories": losing,
        "all_findings": findings,
    }


def main():
    parser = argparse.ArgumentParser(description="Agentic variance panel")
    parser.add_argument("--version", default="v1", choices=["v1", "v2", "v3", "v4"])
    parser.add_argument("--period-a", nargs=2, metavar=("START", "END"),
                        default=["2024-05-01", "2024-05-31"])
    parser.add_argument("--period-b", nargs=2, metavar=("START", "END"),
                        default=["2024-06-01", "2024-06-30"])
    args = parser.parse_args()

    result = asyncio.run(run_panel(
        args.version,
        date.fromisoformat(args.period_a[0]),
        date.fromisoformat(args.period_a[1]),
        date.fromisoformat(args.period_b[0]),
        date.fromisoformat(args.period_b[1]),
    ))

    print("\n" + "="*60)
    print("VARIANCE PANEL RESULT")
    print("="*60)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
