# Roadmap

WinterSolve aims to be the trusted, offline-first way to understand any
repository from the terminal. This page lists what is next; the
[changelog](CHANGELOG.md) lists what is done.

## Now (0.3.x)

- First public release on PyPI and a tagged GitHub release.
- Real-world feedback: run `wintersolve brain .` on many popular repositories
  and fix every false positive, missed command, and awkward sentence it produces.
- Good-first-issue backlog seeded from that exercise.

## Next (0.4)

- Language-aware explainers for TypeScript/JavaScript and Go (symbols, imports,
  exports) to match the Python one.
- Dependency overview: declared dependencies per ecosystem, with counts and
  obviously stale pins, entirely offline.
- Import graph for Python packages, surfaced as "most depended-on modules" in
  the Repo Brain report.
- Monorepo awareness: detect stacks and commands in top-level `apps/*` and
  `packages/*` directories.
- HTML export of the Repo Brain report for sharing and dashboards.

## Later

- Optional AI enhancement of any report from redacted context, clearly marked
  in the output, with local models supported first.
- A minimal, explicit plugin registration API once there are third-party
  analyzers that need it.
- Benchmark fixtures for scan performance on very large repositories.
- Signed release artifacts.

## 1.0 means

- The CLI command contract and JSON schema are stable and documented.
- Every command has snapshot tests on a set of fixture repositories.
- A documented support and deprecation policy.
- At least a handful of real projects using it in CI.

## Non-goals

- No hidden network calls, telemetry, or update checks.
- No AI account required for core value.
- No claims of adoption, audits, or maturity the project has not earned.
