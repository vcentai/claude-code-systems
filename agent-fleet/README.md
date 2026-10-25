# Agent fleet

**One long Claude session plans, codes, tests and then tells you it all works. Nobody checked.**

This is the role set behind a fleet of Claude Code sessions that merged **331 pull requests on 24 Oct 2026** across 43 repositories, with 6 builders and a reviewer running in parallel. Each role does one job and checks the others: the builder must prove its change, the reviewer starts from REJECT and breaks the change on purpose to see the test turn red, the measurer accepts no number without a denominator, and the lead distributes work without writing code.

## The roles

| Role | Job | Never |
|---|---|---|
| `lead` | Measures what is open, cuts work by file ownership, starts the others, merges what the reviewer accepted. | writes code, reviews diffs, measures |
| `builder` | Reaches one goal end to end: reproduce, smallest fix, real test output. | merges, widens the goal, weakens a test |
| `reviewer` | Judges one change against its goal. Default REJECT; reverts the key line to prove the test catches it. | edits code |
| `measurer` | Answers "how many" with denominator, control and negative control. | changes anything |
| `scoper` | Turns a raw backlog into packages a builder can finish without asking; marks what is already obsolete. | builds |
| `watcher` | Judges one case a watch script could not (red nightly job, full disk): NOISE, FINDING or BRAKE. | stays around, fixes |
| `responder` | Answers people outside the repo from what the repo actually says, as a draft. | sends on its own |

**The report protocol.** Every role's final message starts with one word (`DONE`, `STEP`, `QUESTION`, `BLOCKED`, `FINDING`, `OBSOLETE`; the reviewer `ACCEPT`/`REJECT`; the watcher `NOISE`/`FINDING`/`BRAKE`). The lead reads dozens of reports; the first word tells it what to do next. `hooks/report_protocol.py` (SubagentStop) sends a role back once if it forgets.

## Install (4 steps)

1. `mkdir -p .claude/agents .claude/skills .claude/hooks .claude/fleet`
2. Copy `agents/*.md` to `.claude/agents/`, `skills/fleet` to `.claude/skills/`, `hooks/report_protocol.py` to `.claude/hooks/`, `fleet/spawn.sh` to `.claude/fleet/`
3. Merge `settings.json` into `.claude/settings.json`
4. In Claude Code: `/fleet <the work>`, e.g. `/fleet fix the failing tests and add CSV export`

Builders run with `isolation: "worktree"`, so the project must be a git repo with a commit. Pair it with **hook-events** if each worktree needs its own port or database, and with **honesty-hooks** and **finish-what-you-promise** so every role's report is true and finished.

**Scaling out.** Subagents share one session's context. For long waves, `.claude/fleet/spawn.sh <name> "<goal>"` starts a builder as its own headless session in its own worktree (`claude -p --worktree <name> --agent builder`) and writes its report to `.claude/fleet/<name>.md`.

## What it does not do

- It does not make a weak test suite strong. The reviewer catches tests that pass with and without the change; it cannot invent tests for behaviour nobody specified.
- More agents cost more tokens. For a one-line fix, one session is cheaper.
- The 331 figure counts pull requests merged through the fleet's account on that day (333 merged in total, 2 by a dependency bot). GitHub records the account, not whether a human or a session pressed merge.

## Tested

26 Oct 2026, Claude Code 2.1.310, Claude Opus 5.5, in a throwaway Node app with a failing test and Postgres via docker compose, together with the other three systems:

- `/fleet` with two tasks (a failing rounding test, a new 5 % quantity discount). The lead put both into **one** builder because both touch `src/cart.js`, which is the file-ownership rule working. The builder ran in its own worktree and reported `DONE` with red-then-green test output; the reviewer reported `ACCEPT` after recomputing the six new expected values, trying 1,010,000 input combinations, and breaking the code four ways on purpose (`>=` to `>`, rounding removed, percentages added, discount removed): each mutation turned 2 to 4 tests red. The lead merged and ran the suite: **10 of 10** pass, in 2.6 minutes. Both reports were saved in full by `save_subagent_report.py`.
- The lead also listed what it would not decide alone: rounding once vs. per line (a one-cent difference no test pins down) and a test whose name promises more than it checks.
- `hooks/report_protocol.py`: 5 payload cases (missing word blocks, `**DONE**` and `REJECT` pass, other agent types and a second stop pass).
- `fleet/spawn.sh euro-zero2 "<goal>"`: a headless builder in its own worktree reported `DONE`, said honestly that there was no bug to fix, added two tests, proved they can fail (broke the function on purpose: 1 failure), committed on its branch and did not merge: 12 of 12 pass. The first attempt found a real gap: a headless session cannot ask for permissions, so the builder could not edit or run anything and reported `BLOCKED`. `spawn.sh` now grants each role what it needs up front (builder: edits and Bash; all others: read and run).
