# Release Process

Releases are cut from `main` by pushing a `vX.Y.Z` tag. The `Release` workflow
builds the package, checks the tag against `wintersolve.__version__`, publishes
to PyPI with trusted publishing, and creates a GitHub release with generated
notes and the built artifacts attached.

## One-time setup (before the first release)

1. **Create the PyPI project link.** On <https://pypi.org/manage/account/publishing/>
   add a *pending* trusted publisher:
   - PyPI project name: `wintersolve`
   - Owner: `harshitkrhere`, repository: `WinterSolve`
   - Workflow name: `release.yml`
   - Environment name: `release`
2. **Create the `release` environment** in the GitHub repository settings
   (Settings → Environments → New environment → `release`). Optionally add
   yourself as a required reviewer so a tag push cannot publish without a click.
3. Nothing else: no API tokens, no secrets.

## Every release

1. Update `src/wintersolve/__init__.py` (`__version__`) and `CITATION.cff`
   (`version`, `date-released`). `pyproject.toml` reads the version from the
   package, so it needs no edit.
2. Move the `Unreleased` items in `CHANGELOG.md` under the new version heading.
3. Run the full gate locally:

   ```bash
   ruff check . && ruff format --check . && mypy && pytest
   python -m build && python -m twine check --strict dist/*
   ```

4. Open a pull request with the release preparation, merge it after CI passes.
5. Tag and push:

   ```bash
   git tag -a v0.3.0 -m "WinterSolve 0.3.0"
   git push origin v0.3.0
   ```

6. Watch the `Release` workflow. When it finishes, confirm:
   - <https://pypi.org/project/wintersolve/> shows the new version;
   - the GitHub release has the wheel and sdist attached;
   - `pipx install wintersolve==X.Y.Z` works in a clean shell.

## After the release

- Start a fresh `## [Unreleased]` section in `CHANGELOG.md`.
- Add the PyPI badge to the README if this was the first release:

  ```markdown
  [![PyPI](https://img.shields.io/pypi/v/wintersolve.svg)](https://pypi.org/project/wintersolve/)
  ```

- Announce it where the users are (a short post with the sample report works
  better than a feature list).

## Versioning

Semantic versioning. While the major version is `0`, minor releases may change
command output wording; the JSON `schema_version` is bumped whenever fields are
renamed or removed.
