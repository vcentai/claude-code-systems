# Honesty hooks

**Claude says "all tests pass, exit 0". They don't. It read the exit code of `tail`.**

Claude rarely lies on purpose. It reports what a command showed, and some everyday commands show something other than what they seem to measure. Each hook here sits at the exact command where a false report starts, stops it once, and tells Claude the reliable way. Every one exists because of a real incident in a fleet of Claude Code sessions that merged **331 pull requests on 24 Oct 2026**.

| Hook | Catches | Why it exists |
|---|---|---|
| `exit_behind_pipe.py` | `cmd \| tail; echo $?` | `$?` is the exit code of `tail`, almost always 0. A red test run reads as green. Across **22,284** transcripts (1.1 million Bash calls), Claude did this **9,466 times in 3,059 sessions**. |
| `gh_issue_comments.py` | `gh issue view 12` | Prints the body, silently drops the comments, where decisions and reversals sit. Of **8,311** `gh issue view` calls, **3,013** asked for the body without the comments, and **93.5 %** of those were reads that acted on it. A PR once undid a decision that only the third comment contained. |
| `gh_count_control.py` | a count from `gh` (`total_count`, `--jq length`, `\| wc -l`) | `search/issues` does no phrase matching even in quotes (**45 hits, 7 right**); label and search lists returned **0 where 11 and 6 existed**. Asks for a control number next to it. |
| `shared_tmp_path.py` | `> /tmp/test.log` | Parallel sessions overwrite each other's results. **86 of 291** sessions wrote fixed /tmp paths; one file name was used by **12 different sessions**, four of them within 32 minutes. |
| `no_secret_print.py` | `cat .env`, `Read .env`, `grep KEY .env` | Every printed line goes to the API and the transcript. Line tools leak too: `cut -d= -f1` prints the rest of a multi-line PEM key. Three private keys ended up in one worker's transcript that way in two days. |
| `save_subagent_report.py` | (SubagentStop) | A cut-off subagent report looks complete. One worker reported three findings, two were visible, the missing first one was the most important of the run. This writes every report to `.claude/reports/` in full. |

The PreToolUse hooks speak once per session for the "reminder" kind (pipe, gh), then let the command through, because a hook that stops a session 50 times gets switched off. The tmp-path and secrets hooks block every time.

## Install (3 steps)

1. `mkdir -p .claude/hooks && cp hooks/*.py .claude/hooks/` (skip `test_all.py` if you like)
2. Merge `settings.json` into `.claude/settings.json`
3. Add `.claude/reports/` and `tmp/` to `.gitignore`

## What they do not do

- They read the command, not your intent. `exit_behind_pipe` only fires when the pipe is the segment right before `echo $?`; a `$?` in a heredoc or after `> file` is left alone.
- `no_secret_print` knows file names (`.env*`, `*.pem`, `*.key`, `id_rsa*`, `credentials*`, `secrets.*`), not contents. A secret in `config.json` is not covered.
- They cannot make Claude honest about things no command shows. They close the gaps where the tool output itself misleads.

## Tested

`python3 hooks/test_all.py`: each hook's self-test (9, 10, 8, 10, 13 cases), a real hook payload per hook (hit and miss), and Read/Grep payloads for the secrets hook, all green. With two rules broken on purpose, 3 failures, so the tests catch it. Live run on Claude Opus 5.5 with Claude Code 2.1.310 (26 Oct 2026): told to run `npm test 2>&1 | tail -5; echo exit=$?` and to show `.env`, Claude was stopped by `exit-behind-pipe`, `shared-tmp-path` and `no-secret-print`, re-measured with `mktemp` (exit 1, the real result) and listed only the variable names.

The transcript count: `trifft()` from the original hook over every Claude Code transcript on the author's machines, 26 Oct 2026. The other numbers are from the original hooks' incident notes, Aug to Oct 2026.
