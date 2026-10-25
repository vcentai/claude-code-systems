#!/usr/bin/env python3
"""SubagentStop: write every subagent's final report to disk, in full.

A subagent's report is what the lead session acts on. When it is long, what the lead (or you) sees can be
cut, and a cut report looks exactly like a complete one. The first finding of a list is often the one
that got lost.

Writes last_assistant_message to .claude/reports/<YYYY-MM-DD>/<agent_type>-<agent_id>.md in the project
and adds one line to .claude/reports/index.jsonl. Never blocks. Add .claude/reports/ to .gitignore.
"""
import datetime
import json
import os
import re
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    text = data.get("last_assistant_message")
    if not isinstance(text, str) or not text.strip():
        return 0
    root = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    day = datetime.date.today().isoformat()
    kind = re.sub(r"[^\w.-]+", "-", data.get("agent_type") or "agent") or "agent"
    ident = re.sub(r"[^\w.-]+", "-", data.get("agent_id") or "unknown")
    folder = os.path.join(root, ".claude", "reports", day)
    try:
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"{kind}-{ident}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        with open(os.path.join(root, ".claude", "reports", "index.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.datetime.now().isoformat(timespec="seconds"), "agent_type": kind,
                                "agent_id": ident, "chars": len(text), "file": path}) + "\n")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
