# Contributing to WinterSolve

Thank you for considering a contribution to WinterSolve.

WinterSolve is early, so thoughtful ideas, clear docs, useful workflows, and small focused improvements are all valuable.

## Contribution Areas

You can contribute by:

- Proposing developer workflows
- Improving documentation
- Creating prompt templates
- Building CLI commands
- Adding provider integrations
- Writing tests
- Creating example reports
- Reviewing project architecture

## What Makes a Good WinterSolve Contribution

A good contribution should:

- Solve a real developer problem
- Be easy to understand
- Have clear inputs and outputs
- Respect user privacy
- Avoid unnecessary complexity
- Include examples or tests when useful

## Suggested Workflow

1. Open an issue describing the problem.
2. Discuss the proposed workflow or fix.
3. Keep the change focused.
4. Add documentation for user-facing behavior.
5. Submit a pull request with a clear summary.

## Module Contribution Checklist

Before adding a new module, answer:

- What developer problem does this solve?
- Who is the target user?
- What input does the module need?
- What output does it produce?
- How can the output be verified?
- Can it work without exposing private code unnecessarily?

## Technical Guidelines

- Put workflow logic in `src/wintersolve/modules/`.
- Return structured data from modules instead of printing directly.
- Put command-line behavior in `src/wintersolve/cli.py`.
- Put output formatting in `src/wintersolve/report.py`.
- Keep every public command under the clean `wintersolve <workflow>` prefix.
- Add tests in `tests/`.
- Keep offline behavior useful before adding AI provider behavior.
- Use the workflow registry when adding a new public workflow.
- Redact secret-like values before any future provider or export path can expose them.

## Local Development

To set up your environment for local development:

1. Clone the repository and navigate into the root directory.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install the package in editable mode with development dependencies:
   ```bash
   pip install -e .[dev]
   ```
   *Note: If you have `uv` installed, you can speed up this process using:*
   ```bash
   uv pip install -e .[dev]
   ```

To run tests and code quality tools locally:

- **Run tests**:
  ```bash
  pytest
  ```
- **Run linter (Ruff)**:
  ```bash
  ruff check .
  ```
- **Run type checker (Mypy)**:
  ```bash
  mypy src
  ```

