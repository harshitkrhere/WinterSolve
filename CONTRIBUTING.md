# Contributing to WinterSolve

Thanks for looking. WinterSolve is small enough to read in an afternoon, and
most valuable contributions are small too: a new stack marker, a better error
rule, a false positive fixed, a doc that was wrong.

## Set up in two minutes

```bash
git clone https://github.com/harshitkrhere/WinterSolve.git
cd WinterSolve
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pre-commit install               # optional, runs the same checks as CI on commit
```

Check that everything works:

```bash
wintersolve brain .
pytest
```

## The quality gate

CI runs exactly this; run it before opening a pull request:

```bash
ruff check .
ruff format --check .
mypy
pytest
```

`ruff format .` fixes formatting; `ruff check --fix .` fixes the safe lint issues.

## Where things live

| You want to... | Look in |
| --- | --- |
| Detect a new framework, language, or package manager | `modules/scanner.py` (`FRAMEWORK_MARKERS`, `project.py` for extensions) |
| Infer a new command | `modules/command_detector.py` |
| Recognise a new error signature | `modules/debugger.py` (`PATTERNS`) |
| Add or tune a security rule | `modules/security.py` (and `docs/SECURITY_MODEL.md`) |
| Change how a report reads | `report.py`; wording rules in `modules/recommendations.py` |
| Add a command | `cli.py`, then register it in `workflows/registry.py` |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full map and
[BEGINNER.md](BEGINNER.md) for a guided tour with starter tasks.

## Good first contributions

- A framework or tool marker that WinterSolve misses on a repository you know.
- A command that `brain` should have found (attach the manifest file).
- An error message the debugger does not recognise (attach the text).
- A false positive from the security scan (attach the line, redacted if needed).
- A README section synonym the docs assistant should accept.

Each of these is a few lines of code plus a test, and each makes the tool
better for everyone.

## Ground rules for code

- **Offline.** No network calls in the core. Ever.
- **Structured.** Analyzers return frozen dataclasses and never print.
- **Honest.** Heuristic output says it is heuristic; severity is earned.
- **Redacted.** Anything secret-like is redacted before it is stored in a result.
- **Tested.** Use `tmp_path` fixtures from `tests/conftest.py`; never scan the
  WinterSolve repository itself from a test.
- **Readable.** Match the surrounding style: short functions, descriptive names,
  a docstring that says *why* when the *what* is not obvious.

## Pull requests

1. Open an issue first for anything bigger than a small fix, so the design can
   be discussed before the code exists.
2. Keep the change focused; one topic per pull request.
3. Add a line under `Unreleased` in `CHANGELOG.md`.
4. Fill in the pull request template. Mention anything you checked by hand.

Commit messages follow the `type: summary` style already in the history
(`feat:`, `fix:`, `docs:`, `test:`, `chore:`).

## Reporting bugs and ideas

Use the issue templates. For security problems, follow
[SECURITY.md](SECURITY.md) instead of opening a public issue.

## Code of conduct

Be kind, assume good intent, and make space for beginners. See
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
