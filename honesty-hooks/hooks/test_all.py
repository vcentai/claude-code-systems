"""Runs every hook's self-test, then feeds each PreToolUse hook a real hook payload to check the wiring
(exit 2 and a message for a hit, exit 0 and silence otherwise). Run: python3 test_all.py"""
import json
import os
import subprocess
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = ["exit_behind_pipe", "gh_issue_comments", "gh_count_control", "shared_tmp_path", "no_secret_print"]
LIVE = {
    "exit_behind_pipe": ("npm test 2>&1 | tail -5; echo exit=$?", "npm test > out.log 2>&1; echo exit=$?"),
    "gh_issue_comments": ("gh issue view 12", "gh issue view 12 --json title,body,comments"),
    "gh_count_control": ("gh issue list --label bug --json number --jq length", "gh issue list"),
    "shared_tmp_path": ("npm test > /tmp/test.log 2>&1", "npm test > tmp/test.log 2>&1"),
    "no_secret_print": ("cat .env", "cat .env.example"),
}


def run(hook, command):
    payload = json.dumps({"session_id": uuid.uuid4().hex, "hook_event_name": "PreToolUse", "tool_name": "Bash",
                          "tool_input": {"command": command}})
    out = subprocess.run([sys.executable, os.path.join(HERE, f"{hook}.py")], input=payload, capture_output=True, text=True)
    return out.returncode, out.stderr.strip()


def main():
    failures = 0
    for hook in HOOKS:
        r = subprocess.run([sys.executable, os.path.join(HERE, f"{hook}.py"), "--selftest"], capture_output=True, text=True)
        print(f"{hook:20} selftest: {r.stdout.splitlines()[0]}")
        failures += r.returncode != 0
        hit, miss = LIVE[hook]
        code, msg = run(hook, hit)
        ok_hit = code == 2 and msg
        code, msg = run(hook, miss)
        ok_miss = code == 0 and not msg
        print(f"{'':20} payload:  hit {'ok' if ok_hit else 'FAIL'}, miss {'ok' if ok_miss else 'FAIL'}")
        failures += (not ok_hit) + (not ok_miss)
    for tool, args, want in (("Read", {"file_path": "/repo/.env"}, 2), ("Read", {"file_path": "/repo/.env.example"}, 0),
                             ("Grep", {"pattern": "KEY", "path": ".env.local"}, 2),
                             ("Grep", {"pattern": "KEY", "path": ".env", "output_mode": "count"}, 0)):
        payload = json.dumps({"session_id": uuid.uuid4().hex, "tool_name": tool, "tool_input": args})
        out = subprocess.run([sys.executable, os.path.join(HERE, "no_secret_print.py")], input=payload, capture_output=True, text=True)
        ok = out.returncode == want
        print(f"{'no_secret_print':20} {tool} {args}: {'ok' if ok else 'FAIL'}")
        failures += not ok
    print("all green" if not failures else f"{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
