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

Python files are parsed with `ast` (classes, functions, imports, module
docstring, `__main__` guard, syntax errors). Other text files get a lightweight
scan for headings, `function`/`class`/`export` lines, and imports.

`--project` (default: current directory) is a safety fence: files outside it are
refused with exit code `2`.

## `debug` — make sense of an error

```bash
wintersolve debug --text "ModuleNotFoundError: No module named 'demo'"
wintersolve debug --file error.log
npm test 2>&1 | wintersolve debug          # reads stdin when piped
```

Matches known error signatures (Python, Node.js, Go, Rust, JVM, network,
permissions, ports, TLS, auth, dependency conflicts) to likely causes, lists
stack frames it found, and suggests next steps. Exactly one input source is
allowed per run.

## `docs` — documentation health

```bash
wintersolve docs .
wintersolve docs . --draft-readme
```

Checks README headings for the sections readers expect (synonyms count, so
"Getting Started" satisfies both Installation and Usage) and lists missing
hygiene files. `--draft-readme` appends a README skeleton pre-filled with the
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
`evidence`. Branch on `category`; `kind` is the human label.
