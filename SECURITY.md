# Security Policy

WinterSolve runs inside developer repositories, which may contain secrets,
private code, and sensitive logs. We take reports about its behaviour seriously.

## Supported versions

| Version | Supported |
| --- | --- |
| Latest release on PyPI | Yes |
| `main` branch | Yes (best effort) |
| Older releases | No; please upgrade |

## Reporting a vulnerability

Please do **not** open a public issue for security problems.

1. Preferred: use GitHub's private reporting at
   <https://github.com/harshitkrhere/WinterSolve/security/advisories/new>.
2. If that is unavailable, contact the maintainer through their GitHub profile
   (<https://github.com/harshitkrhere>) and mention "WinterSolve security".

Include what you found, how to reproduce it, and what impact you think it has.
You will get an acknowledgement within a few days. Fixes are released as soon
as they are ready, with credit to the reporter unless you prefer otherwise.

## What counts

Examples of things we want to hear about:

- WinterSolve reading or writing outside the directory it was pointed at.
- A secret that reaches a report unredacted.
- Any network activity from the core commands.
- Crashes or hangs caused by crafted repository contents.

False positives and missed detections in the security scan are bugs, not
vulnerabilities: please report them as regular issues (redact any real secret
in the example).

## Guidelines for contributors

Never commit API keys, tokens, passwords, private logs, customer data, or
proprietary code samples. Test fixtures that need "secret-like" strings should
build them from fragments (see `tests/test_security.py`) so the repository's
own scan stays clean.
