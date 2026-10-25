#!/usr/bin/env python3
"""WorktreeRemove: stop the worktree's Docker project, then remove the worktree.

Without it, a removed worktree leaves its containers running and its database volume behind.
Contract (code.claude.com/docs/en/hooks#worktreeremove): JSON on stdin with `worktree_path`.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def log(msg):
    print(f"[worktree-remove] {msg}", file=sys.stderr)


def main():
    path = Path(json.load(sys.stdin)["worktree_path"])
    marker = path / ".env.worktree"
    if marker.is_file() and shutil.which("docker"):
        m = re.search(r"^COMPOSE_PROJECT_NAME=(.+)$", marker.read_text(), re.M)
        if m:
            project = m.group(1).strip()
            r = subprocess.run(["docker", "compose", "-p", project, "down", "--remove-orphans"], cwd=path,
                               capture_output=True, text=True)
            log(f"docker compose -p {project} down: exit {r.returncode}")
    if path.exists():
        r = subprocess.run(["git", "worktree", "remove", "--force", str(path)], cwd=path.parent, capture_output=True, text=True)
        if r.returncode != 0:
            log(r.stderr.strip())
            sys.exit(1)
    log(f"removed {path}")


if __name__ == "__main__":
    main()
