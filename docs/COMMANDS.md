# WinterSolve Commands

## Command Style

All public WinterSolve commands must use the clean prefix:

```text
wintersolve <workflow> [options]
```

Examples:

```powershell
wintersolve brain .
wintersolve scan .
wintersolve explain src/wintersolve/cli.py
```

Do not document public workflows as script paths. Script paths are only development fallbacks.

## `scan`

Inspect a repository and produce a health report.

```powershell
wintersolve scan .
```

Useful for:

- Understanding project structure
- Detecting languages and stack markers
- Finding missing open-source files
- Spotting test and documentation gaps

## `brain`

Build a full project intelligence report.

```powershell
wintersolve brain .
```

Markdown output:

```powershell
wintersolve brain . --format markdown
```

JSON output for tools:

```powershell
wintersolve brain . --format json --output wintersolve-report.json
```

Useful for:

- Understanding a repository quickly
- Mapping architecture and important project areas
- Detecting commands, risks, and missing project hygiene
- Checking security and privacy posture
- Creating contributor onboarding notes

## `explain`

Explain a file using offline static analysis.

```powershell
wintersolve explain src/wintersolve/cli.py
```

Useful for:

- Onboarding into unfamiliar files
- Finding symbols, imports, and file-level risks
- Getting a quick summary before editing

## `debug`

Analyze an error message, log, or stack trace.

```powershell
wintersolve debug --text "ModuleNotFoundError: No module named demo"
```

Or:

```powershell
wintersolve debug --file error.log
```

Useful for:

- Understanding common Python and Node.js errors
- Finding likely causes
- Creating next-step debugging checklists

## `docs`

Suggest documentation improvements.

```powershell
wintersolve docs . --draft-readme
```

Useful for:

- Improving README structure
- Preparing open-source repositories
- Creating starter documentation drafts

## `review`

Review local Git changes and produce a checklist.

```powershell
wintersolve review .
```

Useful for:

- Preparing pull requests
- Checking changed files for risk areas
- Creating review notes before asking others for feedback
