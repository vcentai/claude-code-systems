#!/usr/bin/env python3
"""PreToolUse (Bash): `gh issue view <n>` does not show the comments, and does not say it left them out.

Outside a terminal, plain `gh issue view` prints title and body only; `--comments` prints only the comments
(no title, no body, and on an issue without comments: nothing at all), each with exit code 0. The output
reads as complete. Decisions usually sit in the comments, so Claude acts on a body that a later comment
already overturned.

Blocks `gh issue view` / `gh pr view` unless it asks for JSON that includes `comments`, or asks for status
fields only (no `body`). Suggests the one call that returns everything. Once per session.
Self-test: python3 gh_issue_comments.py --selftest
"""
import json
import os
import re
import sys
import tempfile

VIEW = re.compile(r"\bgh\s+(issue|pr)\s+view\b")

MESSAGE = """gh-issue-comments: `gh {kind} view` hides the comments here, and says nothing about it.

Plain `gh {kind} view` prints the body only; `--comments` prints only the comments (on an issue without
comments: nothing). Decisions and reversals usually sit in the comments. Read both in one call:

  gh {kind} view <n> --json title,state,labels,body,comments

(Shown once per session.)"""


def json_fields(cmd):
    m = re.search(r"--json[ =]([\w,]+)", cmd)
    return set(m.group(1).split(",")) if m else None


def hits(cmd):
    for segment in re.split(r"[;&|]+", cmd):
        if not VIEW.search(segment):
            continue
        fields = json_fields(segment)
        if fields is None:
            return True  # plain view, or --comments without --json
        if "comments" in fields:
            continue
        if "body" in fields:
            return True  # body without comments: the same gap with a flag
    return False


def selftest():
    red = ["gh issue view 878", "gh issue view 878 --comments", "gh issue view 12 --json title,body",
           "cd repo && gh pr view 5", "gh issue view 3 -R org/repo"]
    green = ["gh issue view 878 --json title,state,body,comments", "gh issue view 878 --json state,labels",
             "gh issue list --state open", "gh pr view 5 --json state,mergeCommit", "echo gh issue"]
    bad = [c for c in red if not hits(c)] + [c for c in green if hits(c)]
    print(f"{len(red) + len(green) - len(bad)} of {len(red) + len(green)} cases ok")
    for c in bad:
        print("  FAIL", repr(c))
    return 1 if bad else 0


def once(session, name):
    mark = os.path.join(tempfile.gettempdir(), f".claude-hook-{name}-{session}")
    if os.path.exists(mark):
        return False
    try:
        open(mark, "w").close()
    except OSError:
        pass
    return True


def main():
    if "--selftest" in sys.argv:
        return selftest()
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if data.get("tool_name") == "Bash" and hits(cmd) and once(data.get("session_id", "x"), "gh-issue-comments"):
        kind = "pr" if re.search(r"\bgh\s+pr\s+view\b", cmd) else "issue"
        print(MESSAGE.format(kind=kind), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
