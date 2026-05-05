# semantic/CLAUDE.md

## Module Purpose
MCP server exposing the churn metric engine to Claude sessions.
Exactly 4 tools — reliability drops past ~5.

## Stack
- Python + `mcp` SDK (`pip install mcp`)
- Talks to `engine/calculator.py` for computation
- Reads from `data/canonical.csv`

## Tool Discipline
Each tool description says what it does AND what it does not.
A fresh Claude session must pick the right tool on the first try.
Do not add tools without a clear "does not" boundary in the description.

## Running
```bash
python semantic/server.py          # stdio MCP server
```

## Boundaries
- This layer does NOT store state — all computation delegates to `engine/`.
- PII redaction happens in the `PostToolUse` hook (`.claude/hooks/`), not here.
- Never add a fifth tool without removing or merging an existing one first.
