# WinterSolve

WinterSolve is an open-source Developer OS for coders who want to understand, improve, debug, document, and maintain software projects faster.

It is built around **Repo Brain**, an offline-first project intelligence layer that turns a repository into architecture notes, risk signals, command guesses, security checks, documentation health, and next actions without requiring an AI account.

## Overview

WinterSolve is an offline-first command-line product that helps developers inspect repositories, understand files, analyze errors, improve documentation, prepare code reviews, and build a practical mental model of a project.

## Why WinterSolve Exists

Developers do not only need a chatbot. They need reusable workflows that turn repeated engineering pain into reliable tools.

WinterSolve focuses on developer problems that show up every day:

- Understanding unfamiliar codebases
- Debugging errors and stack traces
- Generating useful documentation
- Creating project templates
- Reviewing code changes
- Writing tests
- Explaining APIs and architecture
- Automating repetitive setup and maintenance work
- Turning project knowledge into reusable AI workflows

## What Makes WinterSolve Different

WinterSolve is designed to stand out from typical AI coding projects in a few important ways:

- **Workflow-first, not prompt-first**: every feature should solve a repeatable developer problem, not just provide a blank chat box.
- **Open and extensible**: contributors can add tools, adapters, prompts, templates, and integrations as independent modules.
- **Developer-owned AI**: the project should support multiple model providers and local options over time.
- **Codebase-aware by design**: WinterSolve should work with repository structure, docs, tests, issues, and project conventions.
- **Practical outputs**: generated results should become files, patches, reports, checklists, or commands that developers can actually use.
- **Beginner-friendly but senior-useful**: new developers get guidance, while experienced developers get automation and repeatable workflows.
- **Privacy-conscious path**: sensitive code should be handled carefully, with future support for local execution and configurable data sharing.

## Core Toolkit Areas

## Features

- Repository health scanning
- Repo Brain project intelligence reports
- Offline file explanation
- Error and stack trace analysis
- Documentation improvement suggestions
- Local change review checklists
- Security and privacy checks
- Stable JSON output for future integrations
- Open module structure for future AI-powered workflows

### 1. Code Understanding

Tools that help developers understand a codebase quickly:

- Project map generator
- File and dependency explainer
- Architecture summary
- API route explorer
- Onboarding guide generator

### 2. Debugging Assistant

Tools that help diagnose and fix errors:

- Stack trace explainer
- Error-to-fix suggestions
- Log summarizer
- Failing test analyzer
- Dependency and environment checker

### 3. Documentation Automation

Tools that turn project knowledge into useful docs:

- README generator
- API documentation assistant
- Changelog helper
- Contribution guide generator
- Architecture decision record templates

### 4. Project Starters

Reusable templates for common developer needs:

- Full-stack app starter
- API service starter
- CLI tool starter
- AI app starter
- Open-source repository starter

### 5. Code Quality Workflows

AI-assisted workflows for safer changes:

- Pull request summary
- Code review checklist
- Test suggestion generator
- Refactor planning assistant
- Security and dependency review helper

### 6. Automation Modules

Small tools that remove repetitive work:

- Issue triage helper
- Release note generator
- Environment setup checklist
- Config file validator
- Repo health report

## Working CLI

WinterSolve includes a working offline-first CLI.

Run a repository scan:

```powershell
wintersolve scan .
```

Build a full Repo Brain report:

```powershell
wintersolve brain . --format markdown
```

Save a JSON report for tooling:

```powershell
wintersolve brain . --format json --output wintersolve-report.json
```

Generate a Markdown report:

```powershell
wintersolve scan . --format markdown
```

Explain a source file:

```powershell
wintersolve explain src/wintersolve/cli.py
```

Analyze an error:

```powershell
wintersolve debug --text "ModuleNotFoundError: No module named demo"
```

Suggest documentation improvements:

```powershell
wintersolve docs . --draft-readme
```

Review local Git changes:

```powershell
wintersolve review .
```

## Installation

### For Users (recommended)

Install the released package from PyPI:

```bash
pip install wintersolve
```

Or use `pipx` for an isolated, globally available command:

```bash
pipx install wintersolve
```

Then run it from any project:

```bash
cd my-app
wintersolve brain .
```

### For Contributors (development setup)

Clone the repository and install in editable mode with dev dependencies:

```bash
git clone https://github.com/harshitkrhere/WinterSolve.git
cd WinterSolve
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[dev]
```

This installs the package with test, lint, and type-check dependencies. The `wintersolve` command works inside the virtual environment.

### Run Without Installing (quick test)

From the project folder:

```bash
$env:PYTHONPATH="src"; python -m wintersolve scan .
```

Or use the local PowerShell helper:

```powershell
.\scripts\wintersolve.ps1 scan .
```

## Usage

See [docs/COMMANDS.md](docs/COMMANDS.md) for command examples.

See [docs/GITHUB_LAUNCH.md](docs/GITHUB_LAUNCH.md) for GitHub install, app/website usage, JSON integration, and CI examples.

## Development Setup

WinterSolve requires `typer>=0.12` and `rich>=13.0` at runtime.

### Install the `wintersolve` Command

To make this work:

```powershell
wintersolve scan .
```

install the project in editable mode:

```powershell
python -m pip install -e .
```

Then open a new PowerShell window and run:

```powershell
wintersolve scan .
```

Run the tests:

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH="src"; python -m unittest discover -s tests
```

## Testing

WinterSolve uses Python's built-in `unittest` runner. The test suite covers repository scanning, Repo Brain JSON output, command detection, secret redaction, safe path handling, and mixed Python/Node.js project detection.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## Security

See [SECURITY.md](SECURITY.md) for security reporting guidance.

## License

WinterSolve is released under the MIT License. See [LICENSE](LICENSE).

## Suggested Repository Structure

```text
WinterSolve/
  README.md
  docs/
    PROJECT_VISION.md
    ROADMAP.md
    MODULES.md
  examples/
    sample-reports/
  templates/
    prompts/
    project-starters/
  src/
    wintersolve/
      modules/
      providers/
      workflows/
  tests/
```

## Project Values

- Solve real developer problems.
- Prefer useful workflows over flashy demos.
- Keep the core modular.
- Make contribution paths clear.
- Respect developer privacy and project ownership.
- Keep outputs readable, editable, and practical.

## Status

WinterSolve is in the early product foundation stage.

The CLI now includes working `brain`, `scan`, `explain`, `debug`, `docs`, and `review` workflows. The next step is to deepen Repo Brain with richer language analyzers, optional AI enhancement, and GitHub-ready release polish.
