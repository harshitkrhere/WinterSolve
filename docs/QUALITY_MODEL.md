# Quality Model

What "done" means for a change to WinterSolve.

## Every change

- `ruff check .` and `ruff format --check .` pass.
- `mypy` passes (strict, for `src/` and `tests/`).
- `pytest` passes, with new behaviour covered by tests that use temp
  directories and never the network.
- User-visible wording is plain, specific, and honest about uncertainty.

## New or changed analyzers

- Logic lives in `src/wintersolve/modules/`, rendering in `report.py`, wiring in
  `cli.py`, registration in `workflows/registry.py`.
- Results are frozen dataclasses; nothing prints inside an analyzer.
- Security-relevant evidence is redacted before it is stored.
- False-positive risk is considered explicitly: prefer a rule that misses a
  rare case over one that cries wolf on common code.
- `docs/COMMANDS.md`, `docs/MODULES.md`, and the README command table are
  updated when behaviour changes.

## Releases

- CI is green on every supported Python version and on Windows and macOS.
- The package builds, `twine check --strict` passes, and the wheel installs and
  runs in a clean environment (CI does this on every push).
- `CHANGELOG.md` and the version are updated together.
