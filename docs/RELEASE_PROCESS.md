# Release Process

This guide describes the expected release flow for WinterSolve maintainers.

## Pre-Release Checklist

- Confirm `CHANGELOG.md` has an entry for the release.
- Confirm `pyproject.toml` and `src/wintersolve/__init__.py` use the same version.
- Run `python -m ruff check .`.
- Run `python -m ruff format --check .`.
- Run `python -m pytest`.
- From `src/`, run `python -m mypy wintersolve`.
- Run `python -m build`.
- Run `python -m twine check dist/*`.

## Release Steps

1. Update version and changelog.
2. Open a pull request with the release preparation changes.
3. Merge after CI passes.
4. Create and push a tag such as `v0.2.0`.
5. Let the release workflow build artifacts and publish through trusted publishing.
6. Verify the GitHub release notes and published package metadata.

## Post-Release

- Start a new `Unreleased` section in `CHANGELOG.md`.
- Confirm install instructions still work from a clean environment.
- Open follow-up issues for any release problems.
