---
name: fleet
description: Run a wave of work with the agent fleet instead of one long session. The lead cuts the work by file ownership, builders work in parallel worktrees, a reviewer that defaults to REJECT checks every change, a measurer answers every number. Use for "work through these issues", "fix all failing tests", "build this feature", anything that splits into parts.
---

# Run a wave

You are the `lead` for this wave (see `.claude/agents/lead.md`). You do not write code yourself.

1. **Measure what is open and what is in flight.** The task you were given, failing tests, open issues if a tracker is available, `git worktree list`, open branches. Write the list down.
2. **Scope if it is big.** More than about 30 items, or items you cannot judge from their title: start one `scoper` subagent first and plan from its packages.
3. **Cut by file ownership.** One package per goal, owning its files; two packages on one file are one package. Write the packages down with their files and their proof before starting anyone.
4. **Builders in parallel.** For each package a `builder` subagent with `isolation: "worktree"`. Send all independent builders in ONE message. Brief: goal as a state, owned files, the test that proves it, what not to touch, "report with DONE/QUESTION/BLOCKED/FINDING as the first word".
5. **A reviewer per change.** Give the `reviewer` the goal and the branch name, not the builder's summary. REJECT goes back to the same builder, at most twice; then the package is open.
6. **A measurer for every claim** with a number or a comparison.
7. **Merge accepted branches** in dependency order into the current branch, run the whole test suite once, and resolve any conflict by keeping both intents (re-run the tests).

Report: done (with the reviewer's verdict and the final test output), open and why, numbers with denominators.

## Scaling past one session

Subagents share this session's context budget. For long waves, start builders as their own headless sessions instead, each in its own worktree, and read their reports from disk:

    .claude/fleet/spawn.sh fix-rounding "Goal: totals round to whole cents; owns src/cart.js; proof: npm test"

The script starts `claude -p --worktree <name> --agent builder`, writes the report to `.claude/fleet/<name>.md`, and returns at once. Check with `ls .claude/fleet/`, then review as in step 5.
