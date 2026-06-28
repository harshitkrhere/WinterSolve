# Quality Model

WinterSolve uses a layered quality model so contributors know what "done" means.

## Required For Code Changes

- Tests cover new behavior or a clear reason is documented.
- Ruff lint and format checks pass.
- Mypy passes for the package.
- Public command output remains readable and stable.
- Security-sensitive output redacts secret-like values.

## Required For New Workflows

- Workflow logic lives in `src/wintersolve/modules/`.
- CLI behavior lives in `src/wintersolve/cli.py`.
- Report rendering lives in `src/wintersolve/report.py`.
- The workflow is registered in `src/wintersolve/workflows/registry.py`.
- Documentation and tests are updated.

## Release Quality Gates

- CI passes on supported Python versions.
- Package builds successfully.
- Distribution metadata passes `twine check`.
- Changelog and version are updated.
