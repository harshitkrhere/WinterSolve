# WinterSolve Security Model

WinterSolve is designed to run inside developer repositories, including private and sensitive projects.

## Defaults

- WinterSolve runs offline by default.
- No AI provider is called unless a future user explicitly configures one.
- Reports redact common secret-like values.
- File access should remain scoped to the target project.

## Current Security Features

- Secret pattern detection for common tokens and key assignments
- Redacted evidence in reports
- Safe project path resolution for file explanation
- Security and privacy section in Repo Brain reports

## Future Provider Rules

Before any provider receives project content:

- Secret redaction must run.
- The provider must be explicitly configured.
- The report should indicate that AI enhancement was used.
- Users should be able to choose local or remote providers.

