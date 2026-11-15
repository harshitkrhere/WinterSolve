# Security Model

WinterSolve is built to be run inside private repositories, so its own
behaviour has to be predictable.

## What WinterSolve does

- Reads recognised text files under the directory you point it at, skipping
  version-control internals, caches, virtual environments, dependency folders,
  and generated directories such as `.next` and `.next-*`.
- Runs `git status --short` for `review`, and optionally `bandit` for `brain`
  when Bandit is installed and the project contains Python files.
- Writes a report to stdout or to the file you name with `--output`.

## What WinterSolve does not do

- No network calls. There is no telemetry, no update check, no upload.
- No writes inside your project unless you pass `--output` with a path there.
- No reading outside the project root for `explain` (`--project` is a fence).
- No AI provider calls from any command. The provider classes exist as an
  optional extension point and are never invoked by the CLI.

## Redaction

Every evidence line in a security finding passes through `redact_secrets`
before it is stored, so reports are safe to paste into issues. Well-known
token formats become `<redacted-secret>`; `name = value` assignments become
`name=<redacted>`.

## How the security scan works

| Layer | Source | Severity | Applied to |
| --- | --- | --- | --- |
| Known token formats (AWS, GitHub, Stripe, Slack, OpenAI, Anthropic, Google, SendGrid, PEM keys) | regex | `high`, everywhere | every text file, including docs, tests, and `.env*` |
| Hardcoded secret-like assignments (`DB_PASSWORD = "..."`) | regex + guard | `medium`; `low` in test code | every text file |
| Risky code patterns (`eval`/`exec`, `shell=True`, `pickle`/`yaml.load`, SQL built from request data) | regex on code with strings and comments blanked | `medium`; `low` in test code | source files only |
| Bandit | subprocess, medium severity and above | Bandit's own; `low` in test code | Python files from the same discovered inventory |

The guard for secret-like assignments rejects placeholders (`changeme`,
`<your-key>`, `${VAR}`) and code expressions (`self.config.api_key`,
`os.getenv(...)`), and requires the value to mix letters and digits.

**Test code** is any file under a `test`, `tests`, `spec`, or `__tests__`
folder, or named like a test (`test_*.py`, `*_test.go`, `*.test.ts`,
`*.spec.js`, `*_spec.rb`). Tests call `eval`, start debug servers, and use fake
passwords on purpose, so those findings are listed as `low` and do not drive
the report's risks or next actions. A well-known token format is still `high`
in a test: a real key there is still a leak.

When Bandit and a built-in pattern flag the same line, only Bandit's finding is
kept, because it names the exact rule (`B307`, `B102`). Evidence is the flagged
line only.

The report's `status` is `clear` when nothing was found and no eligible checks
were skipped, `low-severity findings only` when every finding is `low`,
`attention needed` for medium or high findings, and `partial` when coverage is
incomplete without a medium or high finding. `skipped_files` counts individual
files omitted, while `skipped_reasons` also records linked or inaccessible
directories, replaced invalid UTF-8 bytes, and unavailable or failed Bandit
runs. Generated and dependency folders are excluded by policy;
their contents are not part of the claimed scan scope. Bandit is optional and
the notes say whether it ran.

Security file reads use eight workers by default, with at most 64 files queued
per batch. `brain --read-workers 1` selects serial reads for storage where
concurrency is unhelpful. Findings are sorted after scanning so worker timing
does not alter report order.

Links and Windows reparse points are excluded during discovery. On POSIX,
opening a text file also refuses a final symlink. On Windows, a malicious
process that replaces a regular file with a link between the check and open
can still race this safeguard; do not run WinterSolve on a tree being actively
modified by an untrusted process. Bandit opens the selected paths in a separate
process, so a concurrent untrusted writer can also replace those paths after
discovery on any platform. WinterSolve rechecks each Bandit target before
launch, runs Bandit from a fresh temporary directory outside the project, and
removes `PYTHONPATH` from its environment so a project-owned `bandit.py` cannot
replace the installed tool through the ordinary module search path.

Findings are leads, not verdicts, and the report says so. Confirm each one
in context before acting on it.

## Reporting a vulnerability in WinterSolve itself

See [SECURITY.md](../SECURITY.md).
