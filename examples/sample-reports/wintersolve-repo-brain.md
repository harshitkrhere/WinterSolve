# WinterSolve Repo Brain

- Project: `WinterSolve`
- Path: `/home/dev/WinterSolve`
- Offline mode: yes

## Languages

- Python: 38
- Markdown: 27
- PowerShell: 2

## Detected Stack

- GitHub Actions
- Python package
- pre-commit

## Source Layout

- src
- src/wintersolve
- src/wintersolve/modules
- src/wintersolve/providers
- src/wintersolve/workflows

## Test Layout

- tests
- tests/__init__.py
- tests/conftest.py
- tests/test_architecture.py
- tests/test_brain.py
- tests/test_cli.py
- tests/test_command_detector.py
- tests/test_debugger.py
- tests/test_docs_assistant.py
- tests/test_explainer.py
- tests/test_project.py
- tests/test_providers.py

## Documentation Health

- README contains the expected core sections.
- Core open-source hygiene files are present.

## Detected Commands

- install editable: `python -m pip install -e .` (pyproject.toml, medium)
- test: `python -m pytest` (pyproject.toml, medium)
- pipx: `pipx install wintersolve` (README.md, medium)
- pytest: `pytest 2>&1 | wintersolve debug` (README.md, medium)
- python: `python -m pip install -e ".[dev]"` (README.md, medium)

## Architecture Map

- .github: GitHub community and automation files; notable: .github/CODEOWNERS, .github/PULL_REQUEST_TEMPLATE.md, .github/dependabot.yml, .github/ISSUE_TEMPLATE/bug_report.md
- docs: Project documentation; notable: docs/ARCHITECTURE.md, docs/COMMANDS.md, docs/INSTALLATION.md, docs/INTEGRATIONS.md
- examples: Example inputs, outputs, or sample projects; notable: examples/github-action.yml, examples/sample-reports/wintersolve-repo-brain.md
- scripts: Developer and automation scripts; notable: scripts/install-wintersolve-command.ps1, scripts/wintersolve.ps1
- src: Application or library source code; notable: src/wintersolve/__init__.py, src/wintersolve/__main__.py, src/wintersolve/cli.py, src/wintersolve/logging_config.py
- templates: Reusable templates and prompts; notable: templates/prompts/codebase-summary.md, templates/prompts/debug-helper.md, templates/prompts/pr-review.md
- tests: Automated tests; notable: tests/__init__.py, tests/conftest.py, tests/test_architecture.py, tests/test_brain.py

## Security and Privacy

- Status: clear
- Offline by default: yes
- Files checked: 82
- Secret-like values are redacted before they appear in any report.
- Bandit ran on Python files (medium and high severity): 0 issue(s).

## Risks

- None detected

## Recommendations

- Nothing urgent. Keep docs, tests, and project metadata current as the project grows.

## Next Actions

- Run the detected test command before making changes.
- Use `wintersolve explain <file>` on the most important source files.
- Use the architecture map as the first contributor onboarding guide.
