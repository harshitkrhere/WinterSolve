# WinterSolve Module Ideas

WinterSolve modules should be small, focused workflows. Each module should accept project context, run a clear task, and produce practical output.

## Module Principles

- One module should solve one recognizable developer problem.
- Inputs and outputs should be explicit.
- Generated content should be editable by humans.
- Modules should avoid hidden magic.
- Modules should be testable without requiring a paid AI provider.

## Initial Modules

### Repo Brain

Purpose: compose WinterSolve analyzers into a complete project intelligence report.

Outputs:

- Project identity
- Language and stack summary
- Architecture map
- Source, test, and docs layout
- Detected commands
- Security and privacy summary
- Risks, recommendations, and next actions

Status: initial implementation exists in `wintersolve brain`.

### Project Scanner

Purpose: understand the structure of a repository.

Outputs:

- Project type
- Main languages
- Important files
- Framework guesses
- Test commands
- Build commands
- Documentation gaps

Status: initial implementation exists in `wintersolve scan`.

### Command Detector

Purpose: infer useful developer commands from project files.

Outputs:

- Install commands
- Test commands
- Build commands
- Run commands
- Source and confidence for each command

Status: initial implementation is used by `wintersolve brain`.

### Security Analyzer

Purpose: detect secret-like values and communicate privacy posture.

Outputs:

- Security status
- Files checked
- Redacted findings
- Offline-by-default privacy notes

Status: initial implementation is used by `wintersolve brain`.

### Architecture Mapper

Purpose: summarize important project areas from repository structure.

Outputs:

- Top-level sections
- Likely purpose
- Notable files

Status: initial implementation is used by `wintersolve brain`.

### Code Explainer

Purpose: explain selected files, folders, or symbols.

Outputs:

- Plain-English explanation
- Dependencies
- Key responsibilities
- Risky or complex areas
- Suggested follow-up files

### Debug Helper

Purpose: analyze errors, logs, and stack traces.

Outputs:

- Likely cause
- Relevant files
- Suggested fixes
- Verification steps
- Prevention tips

### Docs Assistant

Purpose: create or improve developer documentation.

Outputs:

- README sections
- Setup instructions
- API docs
- Contribution notes
- Architecture notes

### Review Assistant

Purpose: help review local changes or pull requests.

Outputs:

- Change summary
- Risk areas
- Missing tests
- Review checklist
- Suggested comments

### Test Assistant

Purpose: recommend or draft tests for changed code.

Outputs:

- Test gaps
- Test cases
- Edge cases
- Suggested test files
