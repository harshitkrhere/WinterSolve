# Security Model

WinterSolve is built to be run inside private repositories, so its own
behaviour has to be predictable.

## What WinterSolve does

- Reads files under the directory you point it at, skipping version-control
  internals, caches, virtual environments, and dependency folders.
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
| Bandit | subprocess, medium severity and above | Bandit's own; `low` in test code | Python files, dependency folders excluded |

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

The report's `status` is `clear` when nothing was found, `low-severity
findings only` when every finding is `low`, and `attention needed` otherwise.

Findings are leads, not verdicts, and the report says so. Confirm each one
in context before acting on it.

## Reporting a vulnerability in WinterSolve itself

See [SECURITY.md](../SECURITY.md).
