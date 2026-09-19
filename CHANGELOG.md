# Changelog

All notable changes to WinterSolve are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.3.1] - 2026-09-19

### Added

- Command detection for pre-commit, tox, nox, just, and Taskfile marker files.

### Fixed

- Community files are recognised by convention instead of exact name:
  `LICENSE.txt`, `Readme.md`, `README.rst`, `COPYING`, `CHANGES.rst`, and
  `History.md` all count. Found by running the tool on Flask and Express,
  which were wrongly told they had no LICENSE and no README.

### Changed

- README section detection understands underlined headings (Markdown setext
  and reStructuredText), reads the README under any conventional name, and
  accepts "Example" as a Usage section.

## [0.3.0] - 2026-09-17

First public release candidate. Everything below compares to the 0.2.0 tree
that was never published.

### Added

- `scan --format json` and `scan --output`, so both scan and brain reports can
  feed other tools. Brain JSON now carries a top-level `schema_version`.
- `brain --no-bandit` to skip the optional Bandit pass on large repositories.
- `debug` reads from stdin when piped (`pytest 2>&1 | wintersolve debug`).
- Security findings carry a `category` (`secret`, `code-pattern`, `bandit`)
  that integrations can branch on.
- Stack detection for pnpm, Yarn, Bun, Deno, Nuxt, Astro, Remix, Tailwind,
  uv, Poetry, Pipenv, Elixir, Flutter, CMake, Make, Docker Compose, Terraform,
  GitHub Actions, GitLab CI, Jenkins, pre-commit, and more.
- Command detection for uv, Poetry, Pipenv, requirements.txt, Go, Cargo,
  Maven, Gradle, Bundler, Composer, Mix, Flutter, Docker, and Docker Compose;
  `package.json` scripts now use the package manager implied by the lockfile.
- Debugger rules for AttributeError, NameError, ImportError, recursion,
  encoding, JSON, missing files, ports in use, timeouts, TLS, auth failures,
  dependency conflicts, segfaults, out-of-memory, and database connections,
  plus JVM detection.
- `explain` reports the module docstring and `__main__` guard for Python files.
- Windows and macOS runners in CI, Python 3.14 in the matrix, a clean-environment
  wheel install check, and a Repo Brain report artifact on every CI run.
- `CITATION.cff`, `.editorconfig`, `.gitattributes`, issue template contact
  links, a documentation index, and an example GitHub Action.

### Changed

- The repository walk visits the tree once and prunes ignored directories
  (`node_modules`, `.venv`, build output, `*.egg-info`) instead of filtering
  after the fact; large repositories scan in a fraction of the time.
- The security scan is far quieter and more honest: Bandit only reports medium
  and high severity, skips dependency folders, and is only invoked when
  installed and when Python files exist; risky-pattern rules ignore prose files,
  comments, and string literals; the "secret-like assignment" rule rejects
  placeholders and code expressions and is rated medium, not high. The report
  states exactly which layers ran.
- Risks, recommendations, and next actions are driven by finding categories
  rather than substring matching, and their wording no longer over-promises.
- README section detection reads Markdown headings (with synonyms such as
  "Getting Started") instead of searching the whole text.
- README commands are only collected from fenced code blocks.
- `--format` is validated (`text`, `markdown`, `json`); unknown values exit 2.
- Reports are printed with terminal markup disabled, so paths like
  `app/[id]/page.tsx` are shown literally.
- Packaging: version is read from `wintersolve.__version__`, license uses the
  SPDX expression form, runtime dependencies are just `typer` and `rich`.
- Docs rewritten to describe what the tool does today; aspirational feature
  lists moved to `docs/VISION.md` and `docs/MODULES.md`.

### Fixed

- A `typer.Exit` raised inside a command was caught by a broad `except` and
  reported as `Error:` with exit code 1.
- Syntax errors found by `explain` were computed but never shown.
- The "unknown provider" error message was missing its f-string prefix.
- `.env` files were not scanned for secrets because they have no extension.
- The pre-commit config referenced a hook (`debug-logger`) that does not exist.
- The OSSF Scorecard workflow failed to publish because of global write
  permissions.

### Removed

- Unfinished, unwired scaffolding for async caching, pydantic settings, plugin
  interfaces, and observability, together with the heavy dependencies they
  would have required.

## [0.2.0] - 2026-06-28

Internal milestone (never published).

### Added

- Open-source readiness pass: packaging, CI, CLI reliability, provider
  extension points, release automation, and community documents.

## [0.1.0]

### Added

- Initial offline-first Repo Brain, scan, explain, debug, docs, review, and
  security workflows.

[Unreleased]: https://github.com/harshitkrhere/WinterSolve/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/harshitkrhere/WinterSolve/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/harshitkrhere/WinterSolve/releases/tag/v0.3.0
