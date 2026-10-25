#!/usr/bin/env python3
"""SessionStart + CwdChanged: export the worktree's own ports into every shell command Claude runs.

A dev server started with plain `node server.js` or `python app.py` does not read .env files; it reads
the environment. CLAUDE_ENV_FILE (code.claude.com/docs/en/hooks#persist-environment-variables) is a file
whose `export` lines Claude Code runs before each Bash command. SessionStart covers `claude --worktree`
sessions; CwdChanged covers Claude moving into a worktree mid-session (Claude Code clears the file on the
next CwdChanged, so leaving the worktree drops the values again).
"""
import json
import os
import re
import shlex
import sys
from pathlib import Path


def find_marker(start):
    p = Path(start).resolve()
    for d in (p, *p.parents):
        if (d / ".env.worktree").is_file():
            return d / ".env.worktree"
        if (d / ".git").exists():
            break
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    target = os.environ.get("CLAUDE_ENV_FILE")
    cwd = data.get("new_cwd") or data.get("cwd") or os.getcwd()
    marker = find_marker(cwd)
    if not target or not marker:
        return 0
    lines = []
    for key, value in re.findall(r"^([A-Z0-9_]+)=(.*)$", marker.read_text(), re.M):
        lines.append(f"export {key}={shlex.quote(value)}")
    with open(target, "a") as f:
        f.write("\n".join(lines) + "\n")
    print(f"worktree env: {len(lines)} variables from {marker}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
