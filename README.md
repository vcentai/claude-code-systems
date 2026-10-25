# Claude Code systems

The hooks and agent setup behind a fleet of Claude Code sessions that merged **331 pull requests in one day** (24 Oct 2026, 43 repositories, 6 builders plus a reviewer). Each folder is one system you copy into your project's `.claude/`, with the incident it exists for and the numbers. Free, no signup, MIT.

| System | Use it when | What you get |
|---|---|---|
| [honesty-hooks](honesty-hooks/) | Claude says "exit 0, all green" and it isn't. | Six hooks at the exact commands where false reports start: exit codes behind a pipe, `gh` issues without comments, `gh` counts without a control, shared `/tmp` files, secrets printed into the chat, cut-off subagent reports. |
| [finish-what-you-promise](finish-what-you-promise/) | You come back and the last line says "Next I'll run the tests." Nothing ran. | A Stop hook that won't let Claude end a turn on a promise: do it, or ask. |
| [agent-fleet](agent-fleet/) | One long session does everything and grades its own homework. | Seven roles (lead, builder, reviewer, measurer, scoper, watcher, responder), `/fleet` to run a wave in parallel worktrees, and a report protocol every role must follow. |
| [hook-events](hook-events/) | Your hooks stop at PreToolUse. | Working hooks for WorktreeCreate/Remove, SessionStart/CwdChanged env, Pre/PostCompact, InstructionsLoaded and PostToolUseFailure, e.g. five sessions on one repo, each with its own ports and database. |

They work alone and together: **agent-fleet** runs builders in worktrees, **hook-events** gives each worktree its own ports and containers, **honesty-hooks** and **finish-what-you-promise** keep every session's reports true and its turns finished.

## Tested

Every system was installed into a throwaway Node app with tests and Postgres via docker compose and run for real on 26 Oct 2026 with Claude Code 2.1.310 on Claude Opus 5.5, loading only the project's own settings (`--setting-sources project,local`). Each folder's README has its run and its own test suite.

## Licence

MIT (`LICENSE`).
