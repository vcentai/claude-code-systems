#!/usr/bin/env python3
"""PreToolUse (Bash): output written to a fixed /tmp path can be someone else's output when you read it.

Two Claude sessions running in parallel both write `> /tmp/test.log`, then each reads "its" result. The
file is there, it is just the other session's. Nobody notices, because nothing failed.

Blocks redirects and `tee` into a fixed name directly under /tmp (or /var/tmp) and points to a path that
is unique to this session. Paths built with mktemp, $$ or a variable pass.
Self-test: python3 shared_tmp_path.py --selftest
"""
import json
import re
import sys

TARGET = re.compile(r"(?:>>?|\btee(?:\s+-a)?)\s*['\"]?(/(?:private/)?(?:var/)?tmp/[A-Za-z0-9._-]+)['\"]?(?=\s|$|;|&|\|)")

MESSAGE = """shared-tmp-path: {path} is a fixed name in a shared directory.

A second Claude session writing the same name overwrites this result, and you would read theirs without
noticing. Use a path that belongs to this session:

  out=$(mktemp -t claude.XXXXXX); cmd > "$out" 2>&1; echo "exit=$?"; tail -20 "$out"
  or a git-ignored folder in the project, e.g. tmp/<task>.log (Claude Code protects writes under .claude/)"""


def target(cmd):
    m = TARGET.search(cmd)
    return m.group(1) if m else None


def selftest():
    red = ["npm test > /tmp/test.log 2>&1", "pytest | tee /tmp/out.txt", "echo hi >> /tmp/notes.md",
           "./gate.sh > /private/tmp/gate.log"]
    green = ['out=$(mktemp); npm test > "$out"', "npm test > tmp/test.log", "cat /tmp/test.log",
             "cmd > /tmp/$$.log", "ls /tmp/", "cmd > /dev/null"]
    bad = [c for c in red if not target(c)] + [c for c in green if target(c)]
    print(f"{len(red) + len(green) - len(bad)} of {len(red) + len(green)} cases ok")
    for c in bad:
        print("  FAIL", repr(c))
    return 1 if bad else 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    path = target((data.get("tool_input") or {}).get("command") or "")
    if path:
        print(MESSAGE.format(path=path), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
