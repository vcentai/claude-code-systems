#!/usr/bin/env python3
"""PreToolUse (Bash): reading a secrets file into the conversation sends every value to the model API
and into the transcript on disk.

`cat .env` is the obvious case. The quiet ones are line-based tools that look safe: `grep KEY .env`,
`cut -d= -f1 .env` and `sed 's/=.*//'` print the continuation lines of a multi-line value in full, so a
private key in PEM format lands in the log anyway.

Blocks Bash commands, Read and Grep calls that print a secrets file (.env, .env.*, *.pem, *.key, id_rsa*, credentials*, secrets.*)
and suggests ways that never print a value. Counting matches (`grep -c`) passes.
Self-test: python3 no_secret_print.py --selftest
"""
import json
import re
import shlex
import sys

SECRET = re.compile(r"(^|/)(\.env(\.[\w.-]+)?|[\w.-]*\.pem|[\w.-]*\.key|id_(rsa|ed25519|ecdsa)[\w.-]*|credentials[\w.-]*|secrets?\.[\w.-]+)$")
READERS = {"cat", "head", "tail", "less", "more", "bat", "strings", "grep", "egrep", "rg", "sed", "awk", "cut", "xxd", "od", "nl"}
SAFE_FILES = re.compile(r"\.env\.(example|sample|template|dist)$")

MESSAGE = """no-secret-print: this prints a secrets file ({path}) into the conversation.

Every line goes to the model API and into the transcript on disk. Line tools are not safe either:
`grep KEY .env` or `cut -d= -f1 .env` print the continuation lines of a multi-line value (a PEM key) in full.

Instead:
  python3 -c "import re,sys;print([l.split('=')[0] for l in open('{path}') if re.match(r'^[A-Z_][A-Z0-9_]*=',l)])"   # names only
  grep -c '^MY_VAR=' {path}          # does it exist (count, no value)
  load it into the command that needs it, e.g. `node --env-file={path} app.js`
If the user really needs to see a value, they open the file themselves."""


def finds(cmd):
    for segment in re.split(r"[;&|]+", cmd):
        try:
            words = shlex.split(segment)
        except ValueError:
            words = segment.split()
        if not words:
            continue
        tool = words[0].split("/")[-1]
        if tool not in READERS:
            continue
        if tool in {"grep", "egrep", "rg"} and any(w in ("-c", "--count", "-l", "-q") for w in words):
            continue
        for w in words[1:]:
            if SECRET.search(w) and not SAFE_FILES.search(w):
                return w
    return None


def selftest():
    red = ["cat .env", "cat .env.local", "grep STRIPE .env", "cut -d= -f1 .env.production", "head -3 config/id_rsa",
           "sed 's/=.*//' .env", "tail -n 20 certs/server.key"]
    green = ["cat .env.example", "grep -c '^MY_VAR=' .env", "node --env-file=.env app.js", "cat README.md",
             "ls -la .env", "git diff -- src/"]
    bad = [c for c in red if not finds(c)] + [c for c in green if finds(c)]
    print(f"{len(red) + len(green) - len(bad)} of {len(red) + len(green)} cases ok")
    for c in bad:
        print("  FAIL", repr(c))
    return 1 if bad else 0


def finds_in_tool(tool, args):
    """Read and Grep reach the same file without Bash; they are checked by their path argument."""
    if tool == "Bash":
        return finds(args.get("command") or "")
    if tool in ("Read", "Grep"):
        if tool == "Grep" and args.get("output_mode") == "count":
            return None
        for key in ("file_path", "path", "glob"):
            value = args.get(key) or ""
            if value and SECRET.search(value) and not SAFE_FILES.search(value):
                return value
    return None


def main():
    if "--selftest" in sys.argv:
        return selftest()
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    path = finds_in_tool(data.get("tool_name"), data.get("tool_input") or {})
    if path:
        print(MESSAGE.format(path=path), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
