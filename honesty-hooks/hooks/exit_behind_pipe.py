#!/usr/bin/env python3
"""PreToolUse (Bash): `cmd | tail; echo $?` reports the exit code of `tail`, not of `cmd`.

`tail` almost always exits 0, so a failing test run, linter or guard reads as green, and the line looks
like a measurement. Claude writes this pattern constantly because it keeps long output short.

Only reported when the pipe sits in the segment IMMEDIATELY before `echo ...$?` on the same line;
`$?` inside a heredoc, after a `> file` redirect, or saved right away (`ec=$?`) is fine. Once per session,
then it lets the command through, because a hook that stops a session 50 times gets disabled.
Self-test: python3 exit_behind_pipe.py --selftest
"""
import json
import os
import re
import sys
import tempfile

ECHO_EXIT = re.compile(r"^\s*echo\b[^\n]*\$\?")

MESSAGE = """exit-behind-pipe: `$?` here measures the LAST command of the pipe, not yours.

  cmd 2>&1 | tail -20; echo $?     <- this is the exit code of `tail`, almost always 0

Measure it directly instead:

  cmd > out.log 2>&1; echo "exit=$?"; tail -20 out.log
  cmd; ec=$?; ...                     # save it immediately
  set -o pipefail; cmd | tail -20     # if the pipe has to stay

(Shown once per session.)"""


def heredoc_lines(cmd):
    inside, marker = set(), None
    for i, line in enumerate(cmd.split("\n")):
        if marker is None:
            m = re.search(r"<<-?\s*['\"]?(\w+)", line)
            if m:
                marker = m.group(1)
            continue
        inside.add(i)
        if line.strip() == marker:
            marker = None
    return inside


def hits(cmd):
    if "$?" not in cmd or "pipefail" in cmd:
        return False
    skip = heredoc_lines(cmd)
    for i, line in enumerate(cmd.split("\n")):
        if i in skip or "$?" not in line:
            continue
        parts = re.split(r";|&&", line)  # not on the & of 2>&1
        for before, after in zip(parts, parts[1:]):
            if ECHO_EXIT.search(after) and "|" in before:
                return True
    return False


def selftest():
    red = ['npm run lint 2>&1 | tail -12; echo "exit: $?"', "./check.sh 2>&1 | tail -20; echo exit=$?",
           'pytest -q | tail -3; echo "$?" && date']
    green = ['npm run lint > log.txt 2>&1; echo "exit=$?"; tail -12 log.txt', "git grep foo; ec=$?; echo $ec",
             "python3 - <<'PY'\nprint('a | b; echo $?')\nPY", "npm test 2>&1 | tail -5",
             "tsc | head -4; tsc > /dev/null; echo $?", "set -o pipefail; npm test | tail -3; echo $?"]
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
    if data.get("tool_name") != "Bash":
        return 0
    if hits((data.get("tool_input") or {}).get("command") or "") and once(data.get("session_id", "x"), "exit-behind-pipe"):
        print(MESSAGE, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
