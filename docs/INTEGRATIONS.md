# Integrations

WinterSolve's JSON output is designed to be consumed by other tools. This page
collects the patterns people use most.

## GitHub Actions: a Repo Brain report on every push

```yaml
name: Repo Brain

on:
  push:
    branches: ["main"]
  pull_request:

permissions:
  contents: read

jobs:
  repo-brain:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - run: python -m pip install wintersolve
      - name: Generate reports
        run: |
          wintersolve brain . --format markdown --output repo-brain.md
          wintersolve brain . --format json --output repo-brain.json
      - name: Show the report in the job summary
        run: cat repo-brain.md >> "$GITHUB_STEP_SUMMARY"
      - uses: actions/upload-artifact@v4
        with:
          name: repo-brain
          path: |
            repo-brain.md
            repo-brain.json
```

The Markdown lands in the Actions job summary, so reviewers see it without
downloading anything. A copy of this workflow lives in
[`examples/github-action.yml`](../examples/github-action.yml).

## Fail the build on high-severity findings

```bash
wintersolve brain . --format json --output report.json
python - <<'EOF'
import json, sys
report = json.load(open("report.json"))
high = [f for f in report["security"]["findings"] if f["severity"] == "high"]
for finding in high:
    print(f"{finding['path']}:{finding['line']}: {finding['kind']}")
sys.exit(1 if high else 0)
EOF
```

Or with `jq`:

```bash
wintersolve brain . -f json | jq -e '[.security.findings[] | select(.severity == "high")] | length == 0'
```

## Pipe errors straight into `debug`

```bash
pytest 2>&1 | wintersolve debug
npm run build 2>&1 | wintersolve debug
```

## Pre-commit hook for the review checklist

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: wintersolve-review
        name: WinterSolve review checklist
        entry: wintersolve review .
        language: system
        pass_filenames: false
        verbose: true
```

## Reading the JSON from other languages

The top-level keys of a `brain` report:

| Key | Type | Notes |
| --- | --- | --- |
| `schema_version` | int | Currently `1`. Bumped only for breaking changes. |
| `identity` | object | `name`, `path`, `exists`, `offline_mode`. |
| `languages` | list | `{"name": "Python", "files": 25}` sorted by count. |
| `stack` | list of strings | Detected frameworks, package managers, and tooling. |
| `source_paths`, `test_paths` | list of strings | Relative, forward-slash paths. |
| `docs_health` | list of strings | Human-readable statements. |
| `architecture` | list | `{"name", "path", "purpose", "notable_files"}`. |
| `commands` | list | `{"name", "command", "source", "confidence"}`. |
| `security` | object | `status`, `files_checked`, `findings[]`, `notes[]`. |
| `risks`, `recommendations`, `next_actions` | list of strings | Ordered most important first. |

Everything is plain JSON: no custom types, no dates, and `sort_keys=True` so
diffs between runs are readable.

## Dashboards, IDE extensions, and portals

Generate the JSON in CI, store it next to the build, and render it wherever
your team already looks: an internal developer portal, a VS Code extension, or
a project onboarding page. Because WinterSolve is offline and deterministic,
the same commit always produces the same report.
