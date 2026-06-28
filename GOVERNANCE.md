# Governance

WinterSolve is currently maintained by its project owner and contributors.

## Decision Making

- Security, privacy, and user trust decisions take priority over feature speed.
- Public commands should stay stable once documented.
- New modules should solve a repeatable developer workflow and return structured data.
- Breaking changes require documentation and a migration note in `CHANGELOG.md`.

## Maintainer Responsibilities

- Keep CI green before releases.
- Review security-sensitive changes carefully.
- Keep contributor instructions accurate.
- Label and triage issues in a predictable way.
- Avoid adding hidden network behavior or unclear data-sharing paths.

## Contributor Path

- First-time contributors can start with docs, tests, examples, command detection, and small analyzer improvements.
- Repeat contributors who demonstrate reliable judgment can be invited to review issues or PRs.
- Maintainer access should be granted slowly and only after trust is established.

## Security Decisions

Security reports are handled privately according to `SECURITY.md`. Public issues should not include live credentials, private code, or sensitive logs.
