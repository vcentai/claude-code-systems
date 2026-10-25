"""Both directions: what must block, and what must pass. A pattern that only catches says nothing about
whether it catches the right thing. Run: python3 test_finish_what_you_promise.py"""
import json
import os
import subprocess
import sys

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "finish_what_you_promise.py")

BLOCK = [
    "The parser is fixed and the unit tests pass.\n\nNext I'll run the integration suite.",
    "Found the cause: the cache key ignores the locale.\n\nI'll now fix the key and add a test.",
    "Let me check the migration before we go further.",
    "I'm going to update the README with the new flag.",
    "Two of three tasks are done.\n\nNow I'll start on the third one.",
]

PASS = [
    "I'll now run the tests.\n\nDone: 42 of 42 pass, output above.",              # promise mid-text, result last
    "The fix is merged and deployed. Tests: 42 of 42.",                            # plain report
    "Shall I also update the docs?",                                               # question to the human
    "Should I merge it now or wait for review?",
    "CI is still running; I'll merge once it is green.",                           # waiting for an outside event
    "The build runs in the background, I'll report when it finishes.",
    "I'll fix it if you want, let me know.",
    "I did not start anything new.",                                               # not an action
    "Yesterday I had already run the migration.",
    "",                                                                            # empty message
]


def run(message, active=False):
    payload = json.dumps({"hook_event_name": "Stop", "stop_hook_active": active, "last_assistant_message": message})
    out = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True)
    return out.returncode, out.stdout.strip()


def main():
    errors = []
    for m in BLOCK:
        code, out = run(m)
        if code != 0 or '"block"' not in out:
            errors.append(f"must block, did not: {m!r}")
        code, out = run(m, active=True)
        if out:
            errors.append(f"must never block twice (stop_hook_active): {m!r}")
    for m in PASS:
        code, out = run(m)
        if out:
            errors.append(f"must pass, blocked: {m!r}")
    total = 2 * len(BLOCK) + len(PASS)
    print(f"{total - len(errors)} of {total} cases ok")
    for e in errors:
        print("  FAIL", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
