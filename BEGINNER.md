# WinterSolve Contributor Learning Path

> **Start here if you are new to the project.** This guide takes you from "never heard of WinterSolve" to "confident contributor" in a structured sequence.

---

## Prerequisites (1–2 days)

| Topic | Resource | Done |
|-------|----------|------|
| Python 3.10+ basics | <https://docs.python.org/3/tutorial> | ☐ |
| Git & GitHub flow | <https://git-scm.com/book> | ☐ |
| Virtual envs / `pip` / `pipx` | <https://packaging.python.org> | ☐ |
| CLI comfort | Run `wintersolve --help` locally | ☐ |

---

## Phase 1: Orientation (30 min)

Read **in this order**:

1. `README.md` — what the tool does, quick commands
2. `docs/COMMANDS.md` — every CLI flag & example
3. `docs/ARCHITECTURE.md` — high-level layers (CLI → Modules → Reports → Providers)
4. `CONTRIBUTING.md` — contribution rules, module checklist
5. `CHANGELOG.md` — recent changes, versioning style

---

## Phase 2: Run & Explore (1 hour)

```bash
# 1. Clone & install
git clone https://github.com/harshitkrhere/WinterSolve.git
cd WinterSolve
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[dev]

# 2. Smoke test every command
wintersolve --version
wintersolve scan .
wintersolve brain . --format markdown
wintersolve explain src/wintersolve/cli.py
wintersolve debug --text "ModuleNotFoundError: foo"
wintersolve docs . --draft-readme
wintersolve review .
wintersolve workflows
```

**Goal**: See every command produce output; note anything confusing.

---

## Phase 3: Codebase Tour (2–3 hours)

Follow the data flow for **one command** (e.g., `scan`):

| File | Role | Read? |
|------|------|-------|
| `src/wintersolve/cli.py` | Typer app, argument parsing, dispatch | ☐ |
| `src/wintersolve/modules/scanner.py` | Core logic: file iteration, language detection, risk rules | ☐ |
| `src/wintersolve/project.py` | File iteration, ignore rules, language map | ☐ |
| `src/wintersolve/report.py` | Renderers: text / markdown / JSON | ☐ |
| `src/wintersolve/models.py` | Dataclasses (ScanResult, BrainReport, etc.) | ☐ |
| `tests/test_scanner.py` | Unit tests for scan logic | ☐ |
| `tests/test_cli.py` | CLI integration tests (CliRunner) | ☐ |

**Exercise**: Add a `print("DEBUG")` in `scan_project`, re-run `wintersolve scan .`, verify you see it.

---

## Phase 4: Test & Quality Loop (30 min)

```bash
# Run full CI locally
ruff check .
ruff format --check .
mypy src/wintersolve
pytest -v
```

**Goal**: Green across the board. If red, read the error, fix, re-run.

---

## Phase 5: First Contribution (Pick One)

| Difficulty | Idea | Files to Touch |
|------------|------|----------------|
| 🟢 Easy | Add a missing framework marker (e.g., `deno.json` → "Deno") | `scanner.py:FRAMEWORK_MARKERS` + test |
| 🟢 Easy | Add a new risk rule (e.g., "no `requirements.txt`") | `scanner.py:_build_risks` + test |
| 🟡 Medium | New CLI subcommand: `wintersolve metrics` (LOC, complexity) | `cli.py`, new `modules/metrics.py`, `report.py`, registry, tests |
| 🟡 Medium | Extend `providers/examples.py` with local Ollama provider | `providers/examples.py`, `providers/base.py`, test |
| 🔴 Hard | Incremental scan cache (mtime + hash) | `scanner.py`, `project.py`, new cache file |

**Workflow**:

1. Open issue describing the change.
2. Branch: `git checkout -b feat/your-idea`.
3. Implement + tests + docs.
4. `ruff check . && ruff format --check . && mypy src/wintersolve && pytest`
5. PR with clear description + `CHANGELOG.md` entry.

---

## Phase 6: Deepen (Ongoing)

| Area | How to Master |
|------|---------------|
| **Module internals** | Pick one module (debugger, docs_assistant, security); read every line; write a new test that breaks, then fix. |
| **Report rendering** | Add a new output format (e.g., HTML) to `report.py`. |
| **Provider system** | Implement a real local LLM provider (Ollama) end-to-end. |
| **CI/CD** | Add a new workflow (e.g., performance benchmark on schedule). |
| **Architecture** | Propose a plugin registry redesign via GitHub Discussion → RFC → PR. |

---

## Phase 7: Maintainer Habits (Monthly)

- Triage new issues / label good-first-issues.
- Review PRs: run CI locally, ask for tests/docs.
- Cut a release: `CHANGELOG.md` → tag → verify PyPI.
- Update roadmap / docs with done items from user feedback.

---

## Key Files Cheat Sheet

```
src/wintersolve/
├── cli.py              # Entry point, all commands
├── __init__.py         # Version, logging exports
├── models.py           # All dataclasses (typed)
├── logging_config.py   # Quiet-by-default logging
├── project.py          # FS utilities (ignore, iterate, read)
├── report.py           # All renderers (text/md/json)
├── modules/
│   ├── scanner.py      # Repo scan logic
│   ├── brain.py        # Composes full report
│   ├── security.py     # Secrets + Bandit
│   ├── debugger.py     # Error pattern matching
│   ├── docs_assistant.py
│   ├── explainer.py    # AST + generic symbols
│   ├── reviewer.py     # Git diff checklist
│   ├── command_detector.py
│   ├── recommendations.py
│   └── architecture.py
├── providers/
│   ├── base.py         # Protocol + config dataclasses
│   └── examples.py     # OpenAI / Anthropic examples
└── workflows/registry.py  # Command metadata
```

---

## First Week Checklist

- [ ] Repo builds, tests pass locally
- [ ] Ran every CLI command once
- [ ] Read 5 core source files end-to-end
- [ ] Opened one "good first issue" PR (even typo fix)
- [ ] Joined GitHub Discussions / Discord (if exists)

---

## Golden Rule

> **Read → Run → Break → Fix → Test → PR**. Repeat.

That's the fastest path from beginner to expert contributor.

---

*Welcome to WinterSolve — happy contributing!*