#!/usr/bin/env python3
"""PreCompact + PostCompact: a record of every compaction, with the summary that replaced the conversation.

After a compaction Claude works from a summary. When it later "forgets" a decision, the question is
whether the summary dropped it. Without a record you cannot check. This writes one line per event to
.claude/compactions/<YYYY-MM-DD>.jsonl (trigger manual/auto, transcript size) and, after the compaction,
the full compact_summary next to it. Never blocks.
"""
import datetime
import json
import os
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    root = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    folder = os.path.join(root, ".claude", "compactions")
    now = datetime.datetime.now()
    entry = {"ts": now.isoformat(timespec="seconds"), "event": data.get("hook_event_name"),
             "session_id": data.get("session_id"), "trigger": data.get("trigger")}
    transcript = data.get("transcript_path")
    if transcript and os.path.exists(transcript):
        entry["transcript_bytes"] = os.path.getsize(transcript)
    try:
        os.makedirs(folder, exist_ok=True)
        summary = data.get("compact_summary")
        if summary:
            name = f"{now:%Y-%m-%d-%H%M%S}-{(data.get('session_id') or 'x')[:8]}.md"
            with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
                f.write(summary)
            entry["summary_file"] = name
            entry["summary_chars"] = len(summary)
        with open(os.path.join(folder, f"{now:%Y-%m-%d}.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
