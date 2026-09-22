# Command Reference

Every public command has the same shape:

```text
wintersolve <command> [target] [options]
```

Run `wintersolve --help` or `wintersolve <command> --help` for the options a
given version supports. Global flags: `--version` / `-V` prints the version;
`--verbose` / `-v` shows debug logging on stderr.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success. |
| `1` | The analysis itself failed (unreadable input, unexpected error). |
| `2` | Invalid usage, or the target could not be analyzed (missing path, no Git repository, unknown format). |

Reports go to **stdout**; errors and logs go to **stderr**, so piping JSON into
another tool is always safe.

## `brain` — full project intelligence report

```bash
wintersolve brain .
wintersolve brain . --format markdown --output REPO_BRAIN.md
wintersolve brain . --format json --output wintersolve-report.json
wintersolve brain . --no-bandit          # skip the optional Bandit pass
```

| Option | Default | Notes |
| --- | --- | --- |
| `--format`, `-f` | `text` | `text`, `markdown`, or `json`. |
| `--output`, `-o` | stdout | Write the report to a file instead. |
| `--no-bandit` | off | Skip Bandit. Useful on large Python repositories or when Bandit is not installed. |

Sections: identity, languages, detected stack, source and test layout,
documentation health, detected commands, architecture map, security and
privacy, risks, recommendations, next actions.

The JSON report carries a top-level `schema_version` (currently `1`). Fields are
only added, never renamed or removed, without bumping it.

## `scan` — quick repository health check

```bash
wintersolve scan .
wintersolve scan . --format markdown
wintersolve scan . --format json --output scan.json
```

Cheaper than `brain`: it only looks at file names and marker files, never at
file contents. Reports languages, stack markers, important and missing files,
likely source and test paths, risks, and recommendations.

## `explain` — one file, explained

```bash
wintersolve explain src/app/main.py
wintersolve explain src/app/main.py --project .
```

What you get depends on the language:

| Language | What `explain` finds |
| --- | --- |
| Python | Parsed with `ast`: classes (with method counts), functions, imports, module docstring, `__main__` guard, syntax errors. |
| JavaScript, TypeScript, Vue, Svelte | Top-level functions (including arrow functions), classes, interfaces, types, enums, exports; `import`, `require()`, and dynamic imports, multi-line ones included. |
| Go | Types with their method counts, functions, and every import in `import ( ... )` blocks. |
| Rust, Java, Kotlin, C#, C, C++, Ruby, PHP, shell, PowerShell | Top-level definitions and imports or includes, from line patterns. |
| Markdown, reStructuredText | The outline (headings three levels deep). |
| JSON, TOML, YAML | Top-level keys or tables; JSON that does not parse is reported (JSON with comments is accepted). |

For Python, JavaScript/TypeScript, Go, and Rust the summary also sorts imports
into standard library, third-party, and this project. For most code files the
summary quotes the author's header comment (a Go package doc, a JSDoc file
comment, a Rust `//!` line), skipping licence headers. Other languages get the
line count and a plain note that definitions are not detected for them yet.

`--project` (default: current directory) is a safety fence: files outside it are
refused with exit code `2`.

## `debug` — make sense of an error

```bash
wintersolve debug --text "ModuleNotFoundError: No module named 'demo'"
wintersolve debug --file error.log
npm test 2>&1 | wintersolve debug          # reads stdin when piped
```

Matches known error signatures (Python, JavaScript and Node.js, Go, Rust, JVM,
network, permissions, ports, TLS, auth, dependency conflicts) to likely causes,
lists the error message and stack frames it found, and suggests next steps.
Exactly one input source is allowed per run.

Next steps are specific when the error allows it:

```text
$ wintersolve debug --text "ModuleNotFoundError: No module named 'cv2'"
...
Next steps:
  - `cv2` is provided by the `opencv-python` package: `python -m pip install opencv-python`.
  - Install into the environment that runs the code: activate the virtual environment first, ...
```

It does the same for npm packages and relative paths ("Cannot find module"),
busy ports, and commands missing from PATH. With a stack trace, the first step
points at the deepest frame in your own code, skipping `site-packages`,
`node_modules`, and the runtime.

## `docs` — documentation health

```bash
wintersolve docs .
wintersolve docs . --draft-readme
```

Checks README headings for the sections readers expect (synonyms count, so
"Getting Started" satisfies both Installation and Usage) and lists missing
hygiene files. A dedicated file counts for its topic: with a CONTRIBUTING file
the README is not asked for Development, Testing, or Contributing sections, and
the same goes for SECURITY and LICENSE. Like GitHub, WinterSolve accepts
README, CONTRIBUTING, SECURITY, and CODE_OF_CONDUCT files in `.github/` or
`docs/` as well as at the root. `--draft-readme` appends a README skeleton pre-filled with the
detected stack.

## `review` — pre-review checklist

```bash
wintersolve review .
```

Reads `git status` (not diffs) and turns changed file names into review risks
and a checklist. Exit code `2` when the directory is not a Git repository.

## `workflows` — what is available

```bash
wintersolve workflows
```

Prints the registry of commands with their output formats.

## Using the JSON output

```bash
wintersolve brain . --format json | jq '.security.findings[] | select(.severity == "high")'
wintersolve brain . --format json | jq -r '.commands[] | "\(.name): \(.command)"'
```

Each security finding has `path`, `line`, `category` (`secret`, `code-pattern`,
or `bandit`), `kind`, `severity` (`high`, `medium`, `low`), and redacted
`evidence`. Branch on `category`; `kind` is the human label. Findings in test
code are `low`; see [SECURITY_MODEL.md](SECURITY_MODEL.md) for the full rule.

`security.status` is `clear` (no findings), `low-severity findings only`, or
`attention needed` (at least one `medium` or `high`).
