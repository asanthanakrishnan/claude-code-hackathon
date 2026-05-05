#!/usr/bin/env python3
"""
PostToolUse hook — deterministically redacts PII from tool results.

Triggered after any MCP tool call that returns row-level subscription data.
Replaces customer_name and customer_email with redacted placeholders.

Why a hook, not a prompt instruction:
- Hooks are deterministic: they run every time, unconditionally.
- Prompt instructions are probabilistic: they can be overridden, forgotten, or
  misapplied when context is long.
- PII redaction is a hard requirement, not a preference. It belongs in a hook.

See decisions/adr-hooks-vs-prompts.md for the full ADR.

Input (stdin): JSON with tool_name and tool_result fields (Claude Code hook contract)
Output (stdout): JSON with tool_result.content[*].text fields redacted
"""

import json
import re
import sys

EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
# Matches typical names: "First Last" patterns in JSON string values
NAME_PATTERN = re.compile(r'"customer_name"\s*:\s*"([^"]+)"')
EMAIL_KEY_PATTERN = re.compile(r'"customer_email"\s*:\s*"([^"]+)"')


def redact_text(text: str) -> str:
    # Redact customer_name JSON fields
    text = NAME_PATTERN.sub('"customer_name": "[REDACTED]"', text)
    # Redact customer_email JSON fields
    text = EMAIL_KEY_PATTERN.sub('"customer_email": "[REDACTED]"', text)
    # Catch any bare email addresses not in a named field
    text = EMAIL_PATTERN.sub('[REDACTED_EMAIL]', text)
    return text


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        # Not JSON — pass through unchanged
        sys.stdout.write(raw)
        return

    tool_name = payload.get("tool_name", "")
    tool_result = payload.get("tool_result", {})

    # Only redact for tools that can return row-level customer data
    redact_tools = {"get_metric", "compare_periods"}
    if tool_name not in redact_tools:
        sys.stdout.write(raw)
        return

    content = tool_result.get("content", [])
    for item in content:
        if item.get("type") == "text" and "text" in item:
            item["text"] = redact_text(item["text"])

    payload["tool_result"]["content"] = content
    sys.stdout.write(json.dumps(payload))


if __name__ == "__main__":
    main()
