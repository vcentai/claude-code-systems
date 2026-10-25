# Hook events you are probably not using yet

**Your hooks stop at PreToolUse and Stop. Claude Code fires 30+ events, and some of them fix problems you blame on the model.**

Six working hooks for the newer events, each one solving a concrete problem. All payload fields checked against [code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks) on 26 Oct 2026.

| Event | Hook | The problem it solves |
|---|---|---|
| `WorktreeCreate` | `worktree_create.py` | Five Claude sessions on one repo, all on port 3000 and one database. Gives each worktree its own ports and Docker project. |
| `WorktreeRemove` | `worktree_remove.py` | Removing a worktree leaves its containers and volumes running. Stops them first. |
| `SessionStart` + `CwdChanged` | `worktree_env.py` | `node server.js` reads the environment, not `.env.local`. Exports the worktree's ports into every shell command via `CLAUDE_ENV_FILE`. |
| `PreCompact` + `PostCompact` | `compaction_log.py` | "Claude forgot what we decided." Was it in the summary? Saves every compaction summary so you can check. |
| `InstructionsLoaded` | `instructions_log.py` | "Claude ignores my rule." Often the rule never loaded (glob did not match, nested file never touched). Logs every CLAUDE.md and rules file with load reason and size. |
| `PostToolUseFailure` | `tool_failure_hint.py` | Claude retries a failing command, or kills a process it doesn't own. Adds the concrete fix for known failures (port taken, module missing, auth, rejected push) next to the error. |

For `SubagentStop`, see `save_subagent_report.py` in **honesty-hooks** and `report_protocol.py` in **agent-fleet**.

## Install (3 steps)

1. `mkdir -p .claude/hooks && cp hooks/*.py .claude/hooks/`
2. Merge `settings.json` into `.claude/settings.json` (take only the events you want)
3. Add `.claude/worktrees/`, `.claude/compactions/` and `.claude/instructions/` to `.gitignore`; in `docker-compose.yml` publish `"${DB_PORT:-5432}:5432"` instead of a fixed port

Then `claude --worktree auth`, `claude --worktree billing`, ... each get their own ports.

## How the worktree hooks work

`worktree_create.py` replaces Claude Code's built-in worktree setup, so it does everything itself:

1. creates `.claude/worktrees/<name>` on branch `worktree-<name>`
2. copies untracked env files, the untracked `.claude/` folder (a global gitignore often excludes it, and then the worktree starts without your hooks, agents and skills), and every file listed in `.worktreeinclude`, which Claude Code stops processing once you define this hook
3. clones `node_modules` copy-on-write where the file system can (APFS, Btrfs/XFS reflink)
4. picks a free slot per worktree name and shifts every `PORT` and `*_PORT` by it (`PORT=3000` becomes e.g. `3200` in one worktree and `3490` in another), checks that all shifted ports are free, and sets `COMPOSE_PROJECT_NAME`
5. writes those values into the worktree's own `.env` and `.env.local` (replacing the keys, not duplicating them; a tracked `.env` is left alone) and into `.env.worktree`, which `worktree_env.py` exports into Claude's shell

Writing `.env` matters: `docker compose` reads `.env`, not `.env.local`, for `${DB_PORT}` and the project name. The first version of this hook only wrote `.env.local`, and all five worktrees published Postgres on 5432. The test below caught it.

## What it does not do

- A shared remote resource (one staging database, one third-party sandbox) still collides. Give each session its own or let one session own it.
- `compaction_log.py` and `instructions_log.py` only record; they never block.
- `tool_failure_hint.py` knows five failure patterns. Add your project's recurring ones to `RULES`.

## Tested

26 Oct 2026, Claude Code 2.1.310, in a throwaway Node app with Postgres via docker compose:

- Five worktrees from the hook: compose resolved five different projects and ports (5442, 5592, 5632, 5772, 5922); `docker compose up -d` in all five started **5 Postgres containers at once** without a clash. `worktree_remove.py` on all of them: **0** containers left, only the main checkout in `git worktree list`.
- `claude -p --worktree live4 --model opus`: the session's shell had `PORT=3250 DB_PORT=5682 COMPOSE=qa-shop-live4`, and the app answered `{"ok":true,"port":3250,"db":"5682"}` on its own port.
- That run also found the `.claude/` gap: with `.claude/` ignored globally, the first worktree session started with empty variables because its hooks did not exist in the worktree. Fixed in step 2 above.
