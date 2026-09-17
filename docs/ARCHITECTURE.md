# Architecture

WinterSolve is a small, layered Python package. Data flows one way:

```text
CLI (cli.py)  ->  analyzers (modules/)  ->  result dataclasses  ->  renderers (report.py)
```

- **CLI** parses arguments, calls exactly one analyzer, hands the result to a
  renderer, and maps failures to exit codes. It contains no analysis logic.
- **Analyzers** each solve one developer problem. They take explicit inputs
  (a path, some text) and return a frozen dataclass. They never print and never
  touch the network.
- **Renderers** turn a result into text, Markdown, or JSON. They never compute.
- **Repo Brain** (`modules/brain.py`) is the one analyzer that calls the others
  and composes their results into a single report.

## Package map

```text
src/wintersolve/
├── cli.py                  Typer app: commands, exit codes, output handling
├── report.py               text / markdown / json renderers
├── models.py               shared result types (BrainReport, SecurityFinding, ...)
├── project.py              filesystem walk with pruning, text/code detection, path safety
├── logging_config.py       quiet-by-default stderr logging
├── modules/
│   ├── scanner.py          repository health scan (names and markers only)
│   ├── brain.py            composes every analyzer into the Repo Brain report
│   ├── security.py         secret patterns, risky code patterns, optional Bandit
│   ├── command_detector.py install / build / test / run command inference
│   ├── architecture.py     top-level areas and their likely purpose
│   ├── docs_assistant.py   README section and hygiene-file checks, README draft
│   ├── explainer.py        single-file explanation (ast for Python)
│   ├── debugger.py         error signature matching
│   ├── reviewer.py         git status -> review risks and checklist
│   └── recommendations.py  turns findings into risks, recommendations, next actions
├── providers/              optional AI provider interface and examples (never required)
└── workflows/registry.py   the list of public commands and their output formats
```

## Design rules

1. **Offline by default.** Nothing in the core makes a network call. The optional
   provider examples are the only code that can, and only when explicitly used.
2. **One walk.** `project.walk_project` visits the tree once, pruning ignored
   directories (`node_modules`, `.venv`, build output) before descending. Every
   analyzer builds on that walk instead of re-scanning.
3. **Leads, not verdicts.** Security and debug output is heuristic and says so.
   Wording stays humble; severity is honest (`high` only for unambiguous token
   formats).
4. **Stable outputs.** Text output is plain (no colour codes, no terminal markup)
   so it pastes into issues. JSON carries a `schema_version`; fields are added,
   not renamed.
5. **Safe on private code.** Secret-like values are redacted before they reach
   any report, and `explain` refuses paths outside the project root.
6. **Boring types.** Frozen dataclasses everywhere. No framework, no plugin
   loader, no async, until a real need appears.

## Adding an analyzer

1. Write `modules/<name>.py` with a frozen result dataclass and one public
   function that takes explicit inputs.
2. Add a renderer in `report.py`.
3. Add a command in `cli.py` (a few lines: argument, `_run`, `_emit`).
4. Register it in `workflows/registry.py`.
5. Add tests under `tests/` using temp-directory fixtures from `conftest.py`.
6. Document it in `docs/COMMANDS.md` and the README command table.

If the analyzer's result belongs in the Repo Brain report, wire it into
`modules/brain.py` and `models.BrainReport`, and bump `BRAIN_SCHEMA_VERSION`
only if existing JSON fields change shape.
