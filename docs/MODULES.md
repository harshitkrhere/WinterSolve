# Modules

Each module solves one developer problem, takes explicit inputs, and returns a
frozen dataclass. This page is the "what does each one actually do today" list;
see [ARCHITECTURE.md](ARCHITECTURE.md) for how they fit together.

| Module | Command | What it does today |
| --- | --- | --- |
| `scanner` | `scan` (and `brain`) | Languages by extension, stack markers at the repo root, important and missing community files (root, `.github/`, `docs/`), likely source paths (conventional folders, top-level Python packages, or the repository root), likely test paths, basic risks. Never opens source files. |
| `brain` | `brain` | Runs every analyzer below and composes the Repo Brain report. |
| `security` | `brain` | Known token formats (high everywhere), guarded secret-like assignments (medium), risky code patterns on source files with strings and comments blanked (medium), optional Bandit (medium and above), with findings in test code rated low. Deduplicates Bandit overlaps and redacts evidence. |
| `command_detector` | `brain` | `package.json` scripts with the right package manager (npm / pnpm / yarn / bun), pip / uv / poetry / pipenv, Go, Cargo, Maven, Gradle, Bundler, Composer, Mix, Flutter, Docker, Makefile targets, and commands quoted in README code blocks. |
| `architecture` | `brain` | Groups files by top-level directory, assigns a conventional purpose, lists notable files shallow-first. |
| `docs_assistant` | `docs` (and `brain`) | README section detection from headings with synonyms, missing hygiene files, README draft with detected stack. |
| `explainer` | `explain` | Python: `ast` symbols with method counts, imports, docstring, `__main__` guard, syntax errors. JavaScript/TypeScript, Go, Rust, Java, Kotlin, C#, C/C++, Ruby, PHP, shell, PowerShell: top-level definitions, imports, header comment. Markdown/reST outlines; JSON/TOML/YAML top-level keys. Import breakdown (standard library, third-party, local) for Python, JS/TS, Go, Rust. |
| `debugger` | `debug` | Error signature rules (Python, JavaScript/Node.js, Go, Rust, JVM, network, ports, TLS, auth, dependency conflicts), each with its own advice; names the package, port, or command involved; points at the deepest stack frame in your own code. |
| `reviewer` | `review` | `git status` file names to review risks and a pre-PR checklist. |
| `recommendations` | `brain` | Turns scan and security results into risks, recommendations, and next actions; wording stays humble. |

## Ideas that are not built yet

Listed so nobody mistakes them for features:

- Test assistant: suggest missing tests for changed code.
- Dependency analyzer: outdated or vulnerable dependencies (offline where possible).
- Import graph and dead-code hints for Python and TypeScript.
- Changelog and release-note helpers driven by Git history.
- Optional AI enhancement of any report from redacted context.

If you want to build one, open an issue first so the design can be discussed
before the code exists.
