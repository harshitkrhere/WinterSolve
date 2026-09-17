# Vision

WinterSolve should be the first command a developer runs in a repository they
do not know yet, and the last one they run before asking for a review.

## The problem

Understanding a codebase is slow and repetitive: what is this, how do I run it,
where are the tests, what is risky, what should I do first. Chatbots answer
those questions one at a time and forget the answers. Most tooling that helps
needs an account, a cloud service, or a whole editor.

## The bet

A small, offline, deterministic tool that produces a *structured* answer in a
few seconds, in a form you can paste into an issue or feed to another program,
will earn a place in more workflows than another chat window will.

## Flagship experience

```bash
wintersolve brain .
```

One command, no account, no API key, no editor extension. Architecture,
commands, documentation gaps, security leads, risks, and next steps.

## Who it is for

- Developers joining a project or picking up an unfamiliar repository.
- Maintainers who want a consistent health check across many repositories.
- Students and first-time contributors who need a map before a first PR.
- Teams that want repository intelligence inside CI, dashboards, or portals.

## Principles

- **Offline by default.** Core value never depends on a network.
- **Structured, editable output.** Text you can paste; JSON you can parse.
- **Honest heuristics.** Leads are labelled as leads; severity is earned.
- **Useful before clever.** A boring rule that is right beats a smart one that is not.
- **Contributor-friendly.** Small modules, plain dataclasses, tests that run in seconds.

## Where it can grow

- Richer language-aware analyzers (call graphs, dependency edges, dead code).
- More command and stack detection for more ecosystems.
- Optional AI enhancement that receives redacted context and is clearly marked.
- Exporters for dashboards, IDE extensions, and documentation sites.
- A stable plugin surface once real third-party analyzers exist.

## What it will not become

- A service that phones home.
- A tool that needs an AI account for its core features.
- A project that claims adoption, audits, or maturity it has not earned.
