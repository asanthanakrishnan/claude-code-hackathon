"""
MCP Server — Semantic Layer for the Churn Metric Engine

Tools (exactly 4 — reliability drops past ~5):
  get_metric          — compute churn for a version + period
  list_definitions    — enumerate all definition versions with summaries
  explain_calculation — return human-readable rationale for a specific result
  compare_periods     — diff two time periods; returns both results + delta

Run: python semantic/server.py
Requires: mcp[cli] (pip install mcp)
"""

import json
import sys
from datetime import date
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from engine.calculator import calculate, load_canonical
from engine.definitions import REGISTRY, SUMMARIES

server = Server("churn-semantic-layer")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_metric",
            description=(
                "Compute the churn rate for a specific definition version and time period. "
                "Returns the rate value, numerator, denominator, and the definition version tag. "
                "Use this when the user asks for a churn number or rate. "
                "Does NOT compare versions — use compare_periods for that. "
                "Does NOT explain why the number is what it is — use explain_calculation for that."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "version": {
                        "type": "string",
                        "enum": list(REGISTRY.keys()),
                        "description": "Definition version: v1=logo churn, v2=gross revenue (no downgrades), v3=gross revenue (with downgrades), v4=net revenue",
                    },
                    "period_start": {
                        "type": "string",
                        "description": "ISO date, e.g. 2024-06-01. Start of the period to measure.",
                    },
                    "period_end": {
                        "type": "string",
                        "description": "ISO date, e.g. 2024-06-30. End of the period to measure.",
                    },
                },
                "required": ["version", "period_start", "period_end"],
            },
        ),
        Tool(
            name="list_definitions",
            description=(
                "List all available churn definition versions with one-line summaries. "
                "Use this first when the user asks which definition to use, or when they mention "
                "'logo churn', 'revenue churn', 'net churn', or similar without specifying a version. "
                "Does NOT compute any numbers — use get_metric for that."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="explain_calculation",
            description=(
                "Return a human-readable explanation of what a specific definition version counts, "
                "excludes, and how boundary cases are handled. Includes the key thresholds and "
                "any 'gotchas' that cause different versions to disagree. "
                "Use this when the user asks WHY a number is what it is, or asks about edge cases, "
                "grace periods, downgrade thresholds, or boundary conditions. "
                "Does NOT compute numbers — use get_metric for that."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "version": {
                        "type": "string",
                        "enum": list(REGISTRY.keys()),
                        "description": "The definition version to explain.",
                    },
                },
                "required": ["version"],
            },
        ),
        Tool(
            name="compare_periods",
            description=(
                "Compute the same churn version for two different time periods and return both "
                "results plus the absolute and relative delta between them. "
                "Use this when the user asks about trends, period-over-period changes, or "
                "phrases like 'was churn worse in May than June?'. "
                "Does NOT compare different definition versions — for that, call get_metric twice."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "version": {
                        "type": "string",
                        "enum": list(REGISTRY.keys()),
                        "description": "Definition version to use for both periods.",
                    },
                    "period_a_start": {"type": "string", "description": "ISO date, start of period A."},
                    "period_a_end": {"type": "string", "description": "ISO date, end of period A."},
                    "period_b_start": {"type": "string", "description": "ISO date, start of period B."},
                    "period_b_end": {"type": "string", "description": "ISO date, end of period B."},
                },
                "required": ["version", "period_a_start", "period_a_end", "period_b_start", "period_b_end"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    rows = load_canonical()

    if name == "get_metric":
        try:
            result = calculate(
                arguments["version"],
                date.fromisoformat(arguments["period_start"]),
                date.fromisoformat(arguments["period_end"]),
                rows,
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except ValueError as e:
            return [TextContent(type="text", text=json.dumps({"isError": True, "reason": "invalid_input", "detail": str(e)}))]

    if name == "list_definitions":
        result = [{"version": v, "summary": s} for v, s in SUMMARIES.items()]
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    if name == "explain_calculation":
        version = arguments.get("version", "")
        explanations = {
            "v1": {
                "version": "v1",
                "label": "Logo Churn Rate",
                "counts": "Customers (not revenue). One churned customer = 1 regardless of MRR.",
                "numerator": "Customers whose subscription ended in the period AND who did not renew within 30 calendar days of subscription_end.",
                "denominator": "Customers with an active subscription on the first day of the period.",
                "grace_period": "30 calendar days from subscription_end. Renewal within 30 days = not churned.",
                "downgrades": "Not counted. A downgrade is not a churn.",
                "gotcha": "Two definitions of 'churned' cause disagreement: some teams use status=churned, others use absence of renewal. This version uses status=churned with a 30-day grace window.",
            },
            "v2": {
                "version": "v2",
                "label": "Gross Revenue Churn Rate (cancellations only)",
                "counts": "MRR lost from full cancellations only.",
                "numerator": "Sum of MRR for subscriptions that cancelled in the period, within 30-day grace.",
                "denominator": "Sum of MRR for all subscriptions active on the first day of the period.",
                "grace_period": "30 calendar days (same as v1).",
                "downgrades": "Not counted. Disagrees with v3 on this point.",
                "gotcha": "v2 and v3 can diverge by 2-3x in periods with heavy downgrade activity, because v2 ignores all MRR reduction from downgrades.",
            },
            "v3": {
                "version": "v3",
                "label": "Gross Revenue Churn (cancellations + downgrades ≥20%)",
                "counts": "MRR lost from cancellations PLUS MRR delta from significant downgrades.",
                "numerator": "Cancelled MRR + (original_mrr - new_mrr) for downgrades where reduction ≥ 20% of original.",
                "denominator": "Sum of MRR active on the first calendar day of the period.",
                "grace_period": "None. Calendar-month boundary only.",
                "downgrade_threshold": "Reduction must be ≥ 20.0% of original MRR. Exactly 20.0% counts. 19.99% does not.",
                "boundary": "Calendar month. A sub_end on the last day of the prior month is excluded.",
                "gotcha": "No grace period means a customer who let a subscription lapse for 2 days and then renewed looks like churn in v3 but not in v1/v2.",
            },
            "v4": {
                "version": "v4",
                "label": "Net Revenue Churn Rate",
                "counts": "MRR lost (cancellations + downgrades ≥20%) MINUS MRR gained from expansions.",
                "numerator": "gross_lost_mrr - expansion_mrr_delta. Can be negative (net expansion).",
                "denominator": "Sum of MRR active on the first calendar day of the period.",
                "grace_period": "None (same as v3).",
                "expansions": "expansion_to_mrr - mrr (the delta only). Only positive deltas counted.",
                "gotcha": "v4 can show negative churn (net revenue expansion) in high-growth months. This misleads teams who use it as a loss metric without the expansion offset context.",
            },
        }
        if version not in explanations:
            return [TextContent(type="text", text=json.dumps({"isError": True, "reason": "unknown_version", "detail": f"'{version}' not in {list(explanations)}"}))]
        return [TextContent(type="text", text=json.dumps(explanations[version], indent=2))]

    if name == "compare_periods":
        try:
            version = arguments["version"]
            a = calculate(version, date.fromisoformat(arguments["period_a_start"]), date.fromisoformat(arguments["period_a_end"]), rows)
            b = calculate(version, date.fromisoformat(arguments["period_b_start"]), date.fromisoformat(arguments["period_b_end"]), rows)
            delta = None
            if a["value"] is not None and b["value"] is not None:
                delta = round(b["value"] - a["value"], 6)
            result = {
                "version": version,
                "period_a": a,
                "period_b": b,
                "delta_b_minus_a": delta,
                "direction": ("worse" if delta and delta > 0 else "better" if delta and delta < 0 else "flat"),
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except (ValueError, KeyError) as e:
            return [TextContent(type="text", text=json.dumps({"isError": True, "reason": "invalid_input", "detail": str(e)}))]

    return [TextContent(type="text", text=json.dumps({"isError": True, "reason": "unknown_tool", "detail": f"Tool '{name}' not found"}))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
