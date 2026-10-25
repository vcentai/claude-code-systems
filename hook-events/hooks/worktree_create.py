#!/usr/bin/env python3
"""WorktreeCreate: one git worktree per Claude session, with its own ports and Docker project.

Fires for `claude --worktree <name>`, EnterWorktree, subagents with isolation "worktree", background
sessions. The hook REPLACES Claude Code's own worktree setup, so it creates the worktree itself:

  1. `.claude/worktrees/<name>` on branch `worktree-<name>`
  2. copies the untracked env files git does not check out (.env, .env.local, ...)
  3. clones node_modules copy-on-write where the file system can (APFS, reflink), so tests run at once
  4. shifts every PORT / *_PORT by a per-worktree offset and sets COMPOSE_PROJECT_NAME, written into the
     worktree's own .env and .env.local, because `docker compose` reads `.env` (not .env.local) for
     `${DB_PORT}` and the project name, and dotenv-based dev servers read .env.local
  5. writes the same values to .env.worktree, which worktree_env.py exports into Claude's shell

Contract (code.claude.com/docs/en/hooks#worktreecreate): JSON on stdin with `cwd` and `name`; the LAST
stdout line is the worktree path; everything else to stderr; non-zero exit fails the creation.
"""
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

PORT_STEP = 10
SLOTS = 50


def log(msg):
    print(f"[worktree-create] {msg}", file=sys.stderr)


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def tracked(repo, name):
    return subprocess.run(["git", "ls-files", "--error-unmatch", name], cwd=repo, capture_output=True).returncode == 0


def port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def base_ports(repo):
    ports = {}
    for name in (".env", ".env.local"):
        f = repo / name
        if f.is_file():
            for key, value in re.findall(r"^\s*([A-Z0-9_]*PORT)\s*=\s*(\d+)\s*$", f.read_text(errors="ignore"), re.M):
                ports[key] = int(value)
    ports.setdefault("PORT", 3000)
    return ports


def taken_slots(repo):
    taken = set()
    for f in (repo / ".claude" / "worktrees").glob("*/.env.worktree"):
        m = re.search(r"^WORKTREE_SLOT=(\d+)", f.read_text(errors="ignore"), re.M)
        if m:
            taken.add(int(m.group(1)))
    return taken


def pick_slot(repo, name, ports):
    start = int(hashlib.sha1(name.encode()).hexdigest(), 16) % SLOTS
    taken = taken_slots(repo)
    for i in range(SLOTS):
        slot = (start + i) % SLOTS + 1
        if slot not in taken and all(port_free(p + slot * PORT_STEP) for p in ports.values()):
            return slot
    raise SystemExit("no free port slot left; remove old worktrees under .claude/worktrees")


def set_keys(path, values):
    """Replace KEY=... lines in place and append the missing ones, so no file holds a key twice."""
    lines = path.read_text(errors="ignore").splitlines() if path.exists() else []
    done = set()
    for i, line in enumerate(lines):
        m = re.match(r"^\s*(?:export\s+)?([A-Z0-9_]+)\s*=", line)
        if m and m.group(1) in values:
            lines[i] = f"{m.group(1)}={values[m.group(1)]}"
            done.add(m.group(1))
    missing = [f"{k}={v}" for k, v in values.items() if k not in done]
    if missing:
        lines += ["", "# added by worktree-create: this worktree's own ports and Docker project", *missing]
    path.write_text("\n".join(lines) + "\n")


def clone_tree(src, dst):
    for cmd in (["cp", "-c", "-R", str(src), str(dst)], ["cp", "-R", "--reflink=always", str(src), str(dst)]):
        if subprocess.run(cmd, capture_output=True).returncode == 0:
            return True
        shutil.rmtree(dst, ignore_errors=True)
    return False


def main():
    data = json.load(sys.stdin)
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", data.get("name") or "").strip("-.") or "session"
    repo = Path(git("rev-parse", "--show-toplevel", cwd=data.get("cwd") or os.getcwd()))
    path = repo / ".claude" / "worktrees" / name
    branch = f"worktree-{name}"

    common = Path(git("rev-parse", "--git-common-dir", cwd=repo))
    exclude = (common if common.is_absolute() else repo / common) / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    present = exclude.read_text().splitlines() if exclude.exists() else []
    missing = [p for p in ("/.claude/worktrees/", ".env.worktree") if p not in present]
    if missing:
        with exclude.open("a") as f:
            f.write("\n" + "\n".join(missing) + "\n")

    if not path.exists():
        has_branch = subprocess.run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=repo).returncode == 0
        git(*(["worktree", "add", str(path), branch] if has_branch else ["worktree", "add", "-b", branch, str(path), "HEAD"]), cwd=repo)
        log(f"created {path} on {branch}")

    for f in sorted(repo.glob(".env*")):
        if f.is_file() and f.name != ".env.worktree" and not (path / f.name).exists():
            shutil.copy2(f, path / f.name)
            log(f"copied {f.name}")

    # .claude/ itself: when it is not in git (a global gitignore often excludes it), the worktree would start
    # without these hooks, agents and skills. Copy it, minus the worktrees and the logs.
    claude_dir = repo / ".claude"
    if claude_dir.is_dir() and not tracked(repo, ".claude/settings.json") and not (path / ".claude" / "settings.json").exists():
        shutil.copytree(claude_dir, path / ".claude", dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("worktrees", "reports", "compactions", "instructions", "*.log"))
        log("copied untracked .claude/ (hooks, agents, skills, settings)")

    # .worktreeinclude: Claude Code's own list of ignored files to bring along. A WorktreeCreate hook replaces
    # the built-in setup, so the list is honoured here (gitignore syntax, only untracked ignored files).
    if (repo / ".worktreeinclude").is_file():
        listed = subprocess.run(["git", "ls-files", "--others", "--ignored", "--exclude-from=.worktreeinclude"],
                                cwd=repo, capture_output=True, text=True).stdout.split("\n")
        for rel in filter(None, listed):
            src, dst = repo / rel, path / rel
            if src.is_file() and not dst.exists() and not rel.startswith(".claude/worktrees/"):
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        log(f"copied {len([r for r in listed if r])} file(s) from .worktreeinclude")

    nm = repo / "node_modules"
    if nm.is_dir() and not (path / "node_modules").exists():
        log("cloned node_modules (copy-on-write)" if clone_tree(nm, path / "node_modules")
            else "node_modules not cloned (no copy-on-write here); run your install command in the worktree")

    if not (path / ".env.worktree").exists():
        ports = base_ports(repo)
        slot = pick_slot(repo, name, ports)
        offset = slot * PORT_STEP
        values = {k: str(v + offset) for k, v in sorted(ports.items())}
        values["COMPOSE_PROJECT_NAME"] = re.sub(r"[^a-z0-9_-]", "-", f"{repo.name}-{name}".lower())
        (path / ".env.worktree").write_text(f"WORKTREE_SLOT={slot}\nPORT_OFFSET={offset}\n"
                                            + "".join(f"{k}={v}\n" for k, v in values.items()))
        for env in (".env", ".env.local"):
            if (path / env).exists() or env == ".env.local":
                if tracked(repo, env):
                    log(f"{env} is tracked in git, left unchanged; values are in .env.worktree")
                    continue
                set_keys(path / env, values)
        log(f"ports +{offset} (PORT={values['PORT']}), docker project {values['COMPOSE_PROJECT_NAME']}")

    print(path)


if __name__ == "__main__":
    main()
