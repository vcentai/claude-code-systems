#!/usr/bin/env python3
"""Stop hook: Claude may not end its turn with a promise.

A turn in Claude Code ends when Claude's reply contains no tool call. A reply that ends with
"I'll now run the tests" therefore ends the turn, and the tests never run. The session sits idle,
waiting for a "go on" that nobody sends. In unattended sessions (headless workers, background agents)
that is a lost hour, not a lost sentence.

This hook reads Claude's last message. If its LAST paragraph is a first-person promise ("I'll now fix",
"let me run", "next I'll"), it returns {"decision": "block"} with a reason; Claude Code then continues
the turn with that reason as the next instruction. Three guards keep it from nagging:

  1. stop_hook_active: if this hook already blocked once in this stop sequence, never block again.
  2. Only the last paragraph counts. "First I'll check X." followed by the finished result is a report.
  3. A question to the human ("Shall I ...?", "let me know") or a wait for an outside event ("once CI is
     green", "when the build finishes") is a legitimate end of turn, never a promise.

Input: JSON on stdin with last_assistant_message (Claude Code fills it on Stop); the transcript is only a
fallback for older versions. Output: nothing (let it stop) or {"decision":"block","reason":...}.
"""
import json
import re
import sys

PROMISE = [
    r"\bI(\s+will|'ll)\s+(now\s+|then\s+|next\s+|go\s+ahead\s+and\s+)?"
    r"(start|begin|do|build|write|check|run|fix|continue|implement|add|create|update|test|look|investigate|try|move|push|deploy|commit|merge|measure|verify)\b",
    r"\blet me (now\s+)?(start|begin|do|build|write|check|run|fix|continue|implement|add|create|update|test|look|investigate|try)\b",
    r"\bnext,?\s+I(\s+will|'ll)\b",
    r"\bI(\s+am|'m)\s+(now\s+)?going to\b",
    r"\b(now|next)\s+I(\s+will|'ll|\s+am going to)\b",
]

QUESTION = [
    r"\bshall I\b", r"\bshould I\b", r"\bdo you want\b", r"\bwould you like\b", r"\blet me know\b",
    r"\bwhich (one|option)\b", r"\byour (call|decision|approval)\b", r"\?\s*$",
]

WAITING = [
    r"\b(once|when|until|as soon as)\b", r"\bwait(ing|s)?\b", r"\bis (still )?running\b",
    r"\bin the background\b", r"\bafter (the|your)\b",
]

NOT_AN_ACTION = [r"\bnothing\b", r"\bno longer\b", r"\b(have|has|had|was|were|did)\b"]

LAST_CHARS = 400

REASON = (
    "You ended your turn with a PROMISE, not a result, and a turn without a tool call is over no matter "
    "what it says. Nobody will send you \"go on\"; you would just wait. So do what you announced. If it is "
    "not your task after all, or you need a decision, say exactly that in one sentence: a question may end "
    "a turn, a statement of intent may not."
)


def last_paragraph(text: str) -> str:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return parts[-1] if parts else ""


def promises(text: str) -> bool:
    tail = last_paragraph(text)[-LAST_CHARS:].strip()
    if not tail:
        return False
    if any(re.search(p, tail, re.I) for p in QUESTION):
        return False
    if any(re.search(p, tail, re.I) for p in WAITING):
        return False
    for sentence in re.split(r"(?<=[.!;])\s+", tail):
        if any(re.search(p, sentence, re.I) for p in PROMISE) and not any(
            re.search(p, sentence, re.I) for p in NOT_AN_ACTION
        ):
            return True
    return False


def last_message_from_transcript(path: str) -> str:
    try:
        lines = open(path, encoding="utf-8").readlines()
    except OSError:
        return ""
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        msg = entry.get("message")
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            text = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
            if text.strip():
                return text
    return ""


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0  # a broken hook never holds a session
    if data.get("stop_hook_active"):
        return 0
    text = data.get("last_assistant_message")
    if not isinstance(text, str):
        text = last_message_from_transcript(data.get("transcript_path") or "")
    if promises(text):
        json.dump({"decision": "block", "reason": REASON}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
