# Contributor Learning Path

> Start here if you are new. This takes you from "never heard of WinterSolve"
> to a merged pull request in a structured sequence. Skip steps you already know.

## Prerequisites (an hour, or a couple of days if new to all of it)

| Topic | Resource | Done |
| --- | --- | --- |
| Python 3.10+ basics | <https://docs.python.org/3/tutorial> | ☐ |
| Git and the GitHub pull request flow | <https://git-scm.com/book> | ☐ |
| Virtual environments and `pip` | <https://packaging.python.org> | ☐ |
| A terminal you are comfortable in | Run `wintersolve --help` | ☐ |

## Phase 1: Orientation (30 minutes)

Read in this order:

1. [README.md](README.md): what the tool does, with real output.
2. [docs/COMMANDS.md](docs/COMMANDS.md): every command, flag, and exit code.
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): how the layers fit together.
4. [CONTRIBUTING.md](CONTRIBUTING.md): the rules and the quality gate.

## Phase 2: Run it (30 minutes)

```bash
git clone https://github.com/harshitkrhere/WinterSolve.git
cd WinterSolve
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"

wintersolve --version
wintersolve brain .
wintersolve brain . --format json | head -40
wintersolve scan . --format markdown
wintersolve explain src/wintersolve/cli.py
wintersolve debug --text "ModuleNotFoundError: No module named 'foo'"
wintersolve docs . --draft-readme
wintersolve review .
wintersolve workflows
```

Then run it on a repository you know well. Note every sentence that is wrong,
missing, or awkward: that list is your first contributions.

## Phase 3: Follow one command through the code (1 to 2 hours)

Trace `wintersolve scan .`:

| File | Role |
| --- | --- |
| `src/wintersolve/cli.py` | `scan()` collects the arguments and calls `_run` / `_emit`. |
| `src/wintersolve/modules/scanner.py` | `scan_project()` builds a `ScanResult`. |
| `src/wintersolve/project.py` | `walk_project()` lists files once, pruning `node_modules` and friends. |
| `src/wintersolve/report.py` | `render_scan_report()` turns the result into text, Markdown, or JSON. |
| `tests/test_scanner.py`, `tests/test_cli.py` | How the behaviour is pinned down. |

Exercise: add a temporary `print()` in `scan_project`, run `wintersolve scan .`,
see it, then remove it.

## Phase 4: The quality loop (15 minutes)

```bash
ruff check .
ruff format --check .
mypy
pytest
```

All four must be green. If one is red, read the message, fix, and re-run. This
is exactly what CI runs.

## Phase 5: Your first pull request

Pick one:

| Difficulty | Idea | Where |
| --- | --- | --- |
| Easy | Add a stack marker you use (for example, `bunfig.toml` or `Justfile`). | `modules/scanner.py` `FRAMEWORK_MARKERS` + `tests/test_scanner.py` |
| Easy | Add an error signature the debugger misses. | `modules/debugger.py` `PATTERNS` + `tests/test_debugger.py` |
| Easy | Add a README heading synonym (for example, "Setup" for Installation). | `modules/docs_assistant.py` + `tests/test_docs_assistant.py` |
| Medium | Detect commands from a `Justfile` or `Taskfile.yml`. | `modules/command_detector.py` + tests |
| Medium | Give the explainer TypeScript/JavaScript symbol detection. | `modules/explainer.py` + tests |
| Medium | Add an HTML renderer for the Repo Brain report. | `report.py`, `cli.py` (`ReportFormat`), registry, tests |
| Hard | Monorepo awareness: detect stacks in `apps/*` and `packages/*`. | `modules/scanner.py`, `modules/command_detector.py`, tests |

Workflow:

1. Open an issue describing the change (a sentence or two is fine).
2. `git checkout -b feat/your-idea`
3. Implement, with a test that fails before and passes after.
4. Run the quality loop.
5. Add a line under `Unreleased` in `CHANGELOG.md`.
6. Open the pull request and fill in the template.

## Phase 6: Going deeper

| Area | How |
| --- | --- |
| Security rules | Read `modules/security.py` top to bottom; write a test that produces a false positive, then fix it. |
| Report wording | Read `modules/recommendations.py`; make a sentence more specific without making it less true. |
| CI | Read `.github/workflows/ci.yml`; every job is there for a reason you should be able to explain. |
| Architecture | Propose a change in a GitHub issue before writing it; the discussion is half the work. |

## Package map

```text
src/wintersolve/
├── cli.py              commands, exit codes, output
├── report.py           text / markdown / json renderers
├── models.py           shared result dataclasses
├── project.py          filesystem walk, text/code detection, path safety
├── logging_config.py   quiet-by-default logging
├── modules/            one analyzer per file (scanner, security, debugger, ...)
├── providers/          optional AI provider interface and examples
└── workflows/          registry of public commands
tests/                  one test module per source module, temp-dir fixtures
docs/                   user and contributor documentation
examples/               sample reports and a drop-in GitHub Action
```

## Golden rule

Read, run, break, fix, test, pull request. Repeat. Welcome aboard.
