#!/usr/bin/env bash
# Start one fleet role as its own headless Claude Code session in its own git worktree.
#   .claude/fleet/spawn.sh <name> "<brief>" [role]      role defaults to builder
# The report lands in .claude/fleet/<name>.md, the full log in .claude/fleet/<name>.log.
# Returns immediately; the session runs in the background.
#
# A headless session cannot ask you for permission, so it gets what its role needs up front:
#   builder            edits files and runs commands inside its worktree (acceptEdits + Bash)
#   reviewer, measurer, scoper, watcher, responder   read and run, never edit
# Override with FLEET_TOOLS="Read,Grep,..." and pass extra flags with FLEET_CLAUDE_FLAGS="--model opus".
set -euo pipefail
name="${1:?usage: spawn.sh <name> \"<brief>\" [role]}"
brief="${2:?missing brief}"
role="${3:-builder}"
root="$(git rev-parse --show-toplevel)"
dir="$root/.claude/fleet"
mkdir -p "$dir"
case "$name" in *[!A-Za-z0-9._-]*) echo "name may only contain letters, digits, . _ -" >&2; exit 2;; esac
if [ -e "$dir/$name.md" ] || [ -e "$dir/$name.log" ]; then
  echo "a session named $name already ran here; pick another name" >&2; exit 3
fi
if [ "$role" = "builder" ]; then
  tools="${FLEET_TOOLS:-Bash,Read,Edit,Write,Glob,Grep}"; mode="acceptEdits"
else
  tools="${FLEET_TOOLS:-Bash,Read,Glob,Grep}"; mode="default"
fi
read -r -a extra <<< "${FLEET_CLAUDE_FLAGS:-}"
(
  cd "$root"
  claude -p --worktree "$name" --agent "$role" --permission-mode "$mode" --allowedTools="$tools" \
    --output-format text ${extra[@]+"${extra[@]}"} \
    "$brief

When you are finished, your final message is your report: first word DONE, QUESTION, BLOCKED or FINDING." \
    > "$dir/$name.md" 2> "$dir/$name.log" < /dev/null
  echo "exit=$?" >> "$dir/$name.log"
) &
echo "started $role '$name' (pid $!) -> .claude/fleet/$name.md"
