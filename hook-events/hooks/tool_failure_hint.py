#!/usr/bin/env python3
"""PostToolUseFailure: when a Bash command fails for a reason with a known fix, tell Claude the fix.

Claude often answers a failure by retrying the same thing, or by working around it (killing a process it
does not own, installing a package globally). This hook recognises a few failures and adds the concrete
next step as additionalContext next to the error. Extend RULES with your project's recurring failures.
"""
import json
import re
import sys

RULES = [
    (r"EADDRINUSE|address already in use|port is already allocated|Bind for [\d.]+:(\d+) failed",
     "The port is taken, often by another Claude session. Do not kill a process you did not start. Use this "
     "worktree's own port: `echo $PORT $DB_PORT` (set by the worktree hooks), or pick a free one."),
    (r"Cannot find module|ModuleNotFoundError|No module named",
     "A dependency is missing in THIS checkout. Run the project's install command here (npm ci, pip install -r "
     "requirements.txt). In a fresh worktree node_modules may not have been cloned."),
    (r"command not found",
     "The tool is not installed or not on PATH in this shell. Check the project's README or package scripts for "
     "how it is meant to be run (npx, a venv, a Makefile target) before installing anything globally."),
    (r"Permission denied \(publickey\)|could not read Username|Authentication failed",
     "This is an authentication failure, not a code problem. Do not retry in a loop. Report it as BLOCKED with "
     "the exact command; credentials are the human's step."),
    (r"non-fast-forward|Updates were rejected because the tip",
     "The remote branch moved. Fetch and rebase onto it, re-run the tests, then push with --force-with-lease. "
     "Never plain --force."),
]


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if data.get("tool_name") != "Bash" or data.get("is_interrupt"):
        return 0
    error = data.get("error") or ""
    hints = [hint for pattern, hint in RULES if re.search(pattern, error, re.I)]
    if hints:
        json.dump({"hookSpecificOutput": {"hookEventName": "PostToolUseFailure",
                                          "additionalContext": " ".join(hints)}}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
