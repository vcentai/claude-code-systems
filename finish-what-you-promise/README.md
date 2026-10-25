# Finish what you promise

**You come back to a Claude session and the last line says "Next I'll run the integration tests." Nothing ran. It has been waiting for an hour.**

A turn in Claude Code ends the moment Claude replies without a tool call. "I'll now fix it" is text, not a tool call, so the turn is over and the fix never happens. In an interactive session you type "go on". In a headless worker, a background agent or a subagent, nobody does.

This is a `Stop` hook (and the same file as `SubagentStop`) that reads Claude's last message. If the last paragraph is a first-person promise, it blocks the stop and hands Claude one instruction: do what you announced, or ask in one sentence if you need a decision.

## Install (3 steps)

1. `mkdir -p .claude/hooks`
2. Copy `hooks/finish_what_you_promise.py` into `.claude/hooks/`
3. Merge `settings.json` into `.claude/settings.json`

## What it lets through

It is narrow on purpose, because a hook that nags gets switched off:

- **Only the last paragraph counts.** "First I'll check the logs." followed by the finished result is a report.
- **Questions end turns.** "Shall I also update the docs?", "let me know", anything ending in `?`.
- **Waiting is fine.** "CI is still running, I'll merge once it's green" waits for an outside event.
- **Never twice.** If Claude Code says the hook already blocked (`stop_hook_active`), it lets go. No loops.

## Numbers

From running the original version on a fleet of Claude Code sessions (6 workers plus a reviewer, 2026):

- Hand-labelled 88 blocked stops from 7 days: it caught **30 of 39** real promises, and wrongly held **6 of 37** "waiting for CI" endings and **2 of 12** plain reports. That trade-off is why waiting words now always pass.
- Read the message from `last_assistant_message`, not the transcript file: in 5 headless runs the field was right **5 of 5** times; the transcript still lacked the last message in **4 of 5**. Before the switch, **233 of 321** blocks had judged the second-to-last message.
- It stopped the author's own session from ending on a promise **3 times on 25 Oct 2026**, while this library was being built.

## What it does not do

- English patterns only. Add your language's "I'll now ..." forms to `PROMISE` if you work in another one.
- It cannot tell a promise Claude should keep from one it should drop. It hands that back to Claude: do it, or ask.

## Tested

`python3 hooks/test_finish_what_you_promise.py`: 20 of 20 cases. With the loop guard removed on purpose, 15 of 20; with the waiting rule removed, 14 of 20, so the tests catch both.

Live run, 26 Oct 2026, Claude Code 2.1.310, Claude Opus 5.5: told to explain a failing test and end with "Next I'll fix the rounding in src/cart.js.", Claude did exactly that, the hook blocked the stop, and Claude continued: it turned the promise into a question with the concrete fix ("do you want me to apply the fix now (round the result of `total()` in `src/cart.js:8` with `Math.round`)?"). Do it or ask: that is the whole contract.
