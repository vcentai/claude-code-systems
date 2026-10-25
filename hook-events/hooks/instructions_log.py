#!/usr/bin/env python3
"""InstructionsLoaded: which CLAUDE.md and rules files Claude actually loaded, when and why.

"Claude ignored my rule" often means the rule was never loaded: a path-scoped rule whose glob did not
match, a nested CLAUDE.md in a folder Claude never touched, a file that only loaded after compaction.
This writes one line per load to .claude/instructions/<YYYY-MM-DD>.jsonl with the file, its scope, the
load reason (session_start, nested_traversal, path_glob_match, include, compact) and its size in bytes,
so you can see what each session really had in context. Observability only; it cannot block.
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
    path = data.get("file_path") or ""
    entry = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "session_id": data.get("session_id"),
             "file": path, "scope": data.get("memory_type"), "reason": data.get("load_reason"),
             "trigger_file": data.get("trigger_file_path"), "parent": data.get("parent_file_path"),
             "globs": data.get("globs")}
    try:
        entry["bytes"] = os.path.getsize(path)
    except OSError:
        entry["bytes"] = None
    root = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    folder = os.path.join(root, ".claude", "instructions")
    try:
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, f"{datetime.date.today().isoformat()}.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
