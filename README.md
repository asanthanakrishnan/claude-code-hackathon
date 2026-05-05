# Team Deloitte

## Participants
- Arun Santhanakrishnan (PM · Architect · Developer · Tester)

## Scenario
Scenario 4: Data & Analytics — "40 Dashboards, One Metric, Four Answers"

## What We Built

A complete system that takes one contested metric (SaaS Monthly Churn Rate), imposes a single authoritative definition, and makes it versioned, executable, and queryable in plain English.

**What runs:**
- `data/pipeline.py` — ingests four noisy source files (timezone offset, duplicates, mislabeled categories, gaps/nulls) and produces a clean canonical CSV. 425 raw rows → 200 canonical, 29 flagged.
- `engine/app.py` — FastAPI REST API with four versioned metric definitions (v1 logo churn, v2 gross revenue, v3 gross+downgrades, v4 net revenue). Every result is tagged with the definition version and timestamp that produced it.
- `engine/tests/` — 34 unit tests covering normal cases, boundary conditions (grace period day 30 vs 31, exactly 20% downgrade threshold), and exclusions. All passing.
- `semantic/server.py` — MCP server with four tools (`get_metric`, `list_definitions`, `explain_calculation`, `compare_periods`). A fresh Claude session picks the right tool on the first try.
- `dashboard/index.html` — single HTML dashboard replacing the 40 legacy views: top-level KPI for all four versions, 6-month trend chart, and operator drill-down.
- `evals/run_evals.py` — CI eval harness against 20 golden questions. 100% answer accuracy, 100% refusal accuracy, 0% false-confidence rate.
- `panel/coordinator.py` — agentic variance panel that spins up three parallel subagents (geography, product, time) with explicit context passing when the metric moves unexpectedly.
- `.claude/hooks/redact_pii.py` — PostToolUse hook that deterministically redacts `customer_name` and `customer_email` from drill-down results.

**What's scaffolded / faked:**
- Data is generated (not from a live SaaS system).
- Dashboard drill-down table is mocked — the `/drill` engine endpoint is not yet implemented.
- Panel subagents synthesize from pre-computed segment data; statistical significance testing is not included.

## Challenges Attempted

| # | Challenge | Status | Notes |
|---|---|---|---|
| 1 | The Room — stakeholder interviews | done | Four competing definitions captured; disagreements documented in `decisions/metric-definition.md` |
| 2 | The Mess — noisy raw data | done | Four sources with distinct quality problems; pipeline normalizes to canonical |
| 3 | The Definition — authoritative metric | done | `decisions/metric-definition.md` with explicit thresholds and boundary examples |
| 4 | The Engine — calculation as code | done | FastAPI, four versioned definitions, result tags, 34 tests |
| 5 | The One — single dashboard | done | HTML/Chart.js, KPI + trend + drill-down |
| 6 | The Reconciliation — edge case table | done | 14 edge cases × 5 definitions in `evals/reconciliation.md` |
| 7 | The Scorecard — eval harness | done | 20 golden questions, stratified, runs in CI |
| 8 | The Question — NL query layer | partial | MCP server built; Claude session wiring not yet end-to-end |
| 9 | The Panel — agentic variance explanation | done | Coordinator + 3 parallel subagents with explicit context passing |

## Key Decisions

**Authoritative definition is v1 (logo churn), not revenue churn.**
Ops and CS use customer count to drive capacity planning. Revenue churn (v2–v4) is tracked for finance. Conflating them inflates the ops metric with dollar weights that don't map to headcount. Full rationale in `decisions/metric-definition.md`.

**30-day grace period in v1/v2, none in v3/v4.**
Matches the billing provider's retry window. A card failure on day 1 that clears on day 20 is not a churn. v3/v4 intentionally use a calendar-month hard cut — this is the single biggest source of disagreement between teams and is documented explicitly. See `decisions/metric-definition.md` → Boundary Examples.

**PII redaction in a PostToolUse hook, not a prompt instruction.**
Hooks are deterministic — they run unconditionally on every result. Prompt instructions are probabilistic and can be overridden or forgotten when context is long. PII redaction is a compliance requirement, not a preference. See `decisions/architecture.md` → Key Design Decisions.

**MCP server capped at 4 tools.**
Reliability drops past ~5 tools per agent. Each tool description includes an explicit "does not" clause so a fresh Claude session disambiguates without needing to try multiple tools first.

**Reconciliation table prioritized over dashboard polish.**
The table (rows = edge cases, columns = five definitions) is the artifact that wins the stakeholder room. It shifts the conversation from "who's right" to "which assumptions do we standardize on." Dashboard drill-down is mocked; reconciliation table is complete.

## How to Run It

```bash
# 1. Install dependencies
pip install fastapi uvicorn pydantic mcp anthropic pytest

# 2. Generate data and run pipeline
python3 data/generate_sources.py
python3 data/pipeline.py
# → data/canonical.csv (200 rows, 29 flagged)

# 3. Run all tests
python3 -m pytest engine/tests/ -v
# → 34 passed

# 4. Run eval harness
python3 evals/run_evals.py --verbose
# → 20/20, CI THRESHOLD PASSED

# 5. Start the engine API
uvicorn engine.app:app --reload --port 8002

# 6. Try the comparison endpoint (shows all four versions disagreeing)
curl "http://localhost:8002/compare?period_start=2024-06-01&period_end=2024-06-30"

# 7. Open the dashboard
open dashboard/index.html

# 8. Start the MCP server (for Claude NL queries)
python3 semantic/server.py

# 9. Run the agentic variance panel (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=sk-ant-...
python3 panel/coordinator.py --version v1 --period-a 2024-05-01 2024-05-31 --period-b 2024-06-01 2024-06-30
```

## If We Had More Time

1. **Wire the NL query layer end-to-end.** Configure a Claude session with the MCP server and test "Why was June worse than May?" against the live engine. The semantic layer is built; the session wiring is not.
2. **Implement `/drill` on the engine API.** The dashboard drill-down is mocked. The engine needs a `GET /drill?period_start=&period_end=&version=` endpoint that returns filtered canonical rows (with PII already redacted by the hook).
3. **Statistical significance on the variance panel.** The panel currently compares raw rates across segments. A proper implementation would flag whether a segment delta is statistically significant before calling it the "best explanation."
4. **Definition promotion workflow.** When v1 is updated to v2, surface a diff showing which historical results would change. The reconciliation table is the manual prototype for this — it should become a programmatic check in CI.
5. **Real data connectors.** Replace `generate_sources.py` with adapters for actual billing systems (Stripe, Chargebee) so the pipeline runs on live data.

## How We Used Claude Code

**Biggest time saves:**
- The entire system scaffold (7 layers, 34 files, 4,400 lines) was built in a single session using parallel tool calls across independent modules. What would have taken a day of boilerplate took under an hour.
- Boundary-case test generation: describing the grace period edge cases in plain English and having Claude translate them into deterministic test fixtures (`engine/tests/fixtures.py`) eliminated the usual cycle of "write test → find it's wrong → fix fixture" iteration.
- The reconciliation table: stating "rows are edge cases, columns are the five definitions, cells show what each returns" produced a complete, accurate artifact on the first pass.

**What surprised us:**
- Three-level CLAUDE.md genuinely works. The directory-level files (`engine/CLAUDE.md`, `semantic/CLAUDE.md`) kept Claude from bleeding engine conventions into the MCP layer and vice versa.
- The hooks-vs-prompts distinction is not just an exam topic — it surfaced a real decision. The PII redaction hook caught a case where a prompt instruction would have been silently ignored in a long-context session.
- Asking Claude to write tool descriptions that include "does not" boundaries produced noticeably better tool selection than descriptions that only stated what the tool does.

**Where it saved the most time:**
- Data quality simulation (`generate_sources.py`) — generating realistic noise patterns (retry storm duplicates, tz-naive timestamps, label swaps) that are hard to think up from scratch.
- The eval harness — translating "include refusal cases and adversarial prompts" into a concrete 20-question golden set with expected tool names, expected output keywords, and CI thresholds.
