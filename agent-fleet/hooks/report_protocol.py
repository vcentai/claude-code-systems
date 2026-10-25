#!/usr/bin/env python3
"""SubagentStop: a fleet role has not reported until its final message starts with its report word.

"done" at the end of a long transcript is not a report. The lead reads dozens of them; the first word
tells it what to do next without reading the rest: DONE (merge after review), QUESTION (answer now),
BLOCKED (unblock or reassign), FINDING (decide), OBSOLETE (close), STEP (one package done, more coming).

If a fleet role ends without its word, this hook blocks the stop once and asks for the report. Roles not
in ROLE_WORDS (Claude Code's own agents, your other subagents) pass untouched. Never blocks twice.
"""
import json
import re
import sys

ROLE_WORDS = {
    "builder": ("DONE", "STEP", "QUESTION", "BLOCKED", "FINDING"),
    "reviewer": ("ACCEPT", "REJECT"),
    "measurer": ("DONE", "BLOCKED", "FINDING"),
    "scoper": ("DONE", "QUESTION", "BLOCKED"),
    "watcher": ("NOISE", "FINDING", "BRAKE"),
    "responder": ("DONE", "QUESTION"),
}


def first_word(text):
    m = re.match(r"\s*[*_`#>\s]*([A-Z]+)\b", text or "")
    return m.group(1) if m else ""


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if data.get("stop_hook_active"):
        return 0
    words = ROLE_WORDS.get(data.get("agent_type") or "")
    if not words:
        return 0
    if first_word(data.get("last_assistant_message") or "") in words:
        return 0
    reason = (f"You are the {data.get('agent_type')} and you have not reported yet. Your final message must "
              f"start with one of: {', '.join(words)}. Then the evidence (commands and real output). "
              "Write that report now as your final message.")
    json.dump({"decision": "block", "reason": reason}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
