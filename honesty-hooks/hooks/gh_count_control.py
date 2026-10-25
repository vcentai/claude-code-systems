#!/usr/bin/env python3
"""PreToolUse (Bash): a number that comes out of `gh` is often a statement about the query, not the repo.

Three measured ways it goes wrong, all with exit code 0 and healthy-looking output:

  TOO MANY   `gh api search/issues` does no phrase matching, even in quotes: 45 hits, 7 right (16 %).
  TOO FEW    `gh issue list --label` and `gh pr list --search` returned 0 where `gh search` found 11 and 6.
  NOTHING    `gh issue view --comments` prints 0 bytes on an issue without comments.

When Claude is about to count something with gh (`total_count`, `--jq length`, `| wc -l` on a gh list or
search, `--limit` that may cap the result), this reminds it once per session to put a control next to
the number: the unfiltered total, a sample read in full, or a positive control that must hit.
Self-test: python3 gh_count_control.py --selftest
"""
import json
import os
import re
import sys
import tempfile

GH = re.compile(r"\bgh\s+(api\s+[\"']?search/|search\s|issue\s+list|pr\s+list|run\s+list|api\s)")
COUNT = re.compile(r"total_count|--jq\s+'[^']*\blength\b|--jq\s+\"[^\"]*\blength\b|--jq\s+length\b|\|\s*wc\s+-l|\|\s*jq\s+['\"]?[^'\"]*\blength\b")

MESSAGE = """gh-count-control: this number comes from gh and has no control next to it.

The same query can be wrong in three directions, each with exit code 0:
  too many  search/issues does no phrase matching (measured: 45 hits, 7 right)
  too few   --label / --search lists returned 0 where `gh search` found 11 and 6
  nothing   `gh issue view --comments` prints 0 bytes on an issue without comments
Also check --limit: a list capped at 30 or 100 counts the cap, not the repo.

Put a second number next to it: the unfiltered total, a sample you read in full, or a positive control
that MUST hit. A 0 is a statement about your query until a control says otherwise.

(Shown once per session.)"""


def hits(cmd):
    return bool(GH.search(cmd) and COUNT.search(cmd))


def selftest():
    red = ["gh api search/issues -f q='repo:a/b is:open bug' --jq .total_count",
           "gh issue list --label bug --json number --jq length", "gh pr list --search foo | wc -l",
           "gh run list --limit 100 --json conclusion --jq 'map(select(.conclusion==\"failure\")) | length'"]
    green = ["gh issue view 5 --json title,body,comments", "gh pr list --state open", "wc -l file.txt",
             "gh api repos/a/b --jq .default_branch"]
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
    if data.get("tool_name") == "Bash" and hits(cmd) and once(data.get("session_id", "x"), "gh-count-control"):
        print(MESSAGE, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
