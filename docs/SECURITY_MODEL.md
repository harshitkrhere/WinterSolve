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
| Known token formats (AWS, GitHub, Stripe, Slack, OpenAI, Anthropic, Google, SendGrid, PEM keys) | regex | `high` | every text file, including docs and `.env*` |
| Hardcoded secret-like assignments (`DB_PASSWORD = "..."`) | regex + guard | `medium` | every text file |
| Risky code patterns (`eval`/`exec`, `shell=True`, `pickle`/`yaml.load`, SQL built from request data) | regex on code with strings and comments blanked | `medium` | source files only |
| Bandit | subprocess, medium severity and above | Bandit's own | Python files, dependency folders excluded |

The guard for secret-like assignments rejects placeholders (`changeme`,
`<your-key>`, `${VAR}`) and code expressions (`self.config.api_key`,
`os.getenv(...)`), and requires the value to mix letters and digits.

Findings are leads, not verdicts, and the report says so. Confirm each one
in context before acting on it.

## Reporting a vulnerability in WinterSolve itself

See [SECURITY.md](../SECURITY.md).
