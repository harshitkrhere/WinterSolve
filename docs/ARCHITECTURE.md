# WinterSolve Architecture

WinterSolve is designed as an offline-first Developer OS with optional AI provider support later.

## Product Layers

1. **CLI**
   - Parses commands
   - Keeps workflows easy to run from any repository
   - Prints useful reports

2. **Modules**
   - Implement one developer workflow each
   - Keep inputs and outputs explicit
   - Work without paid services whenever possible

3. **Reports**
   - Convert module results into readable output
   - Keep generated content easy to copy into issues, docs, or pull requests

4. **Providers**
   - Future home for AI model integrations
   - Should be optional and configurable
   - Must make privacy behavior clear

5. **Repo Brain**
   - Composes lower-level modules into one project intelligence report
   - Produces stable text, Markdown, and JSON output
   - Includes architecture, commands, security, risks, recommendations, and next actions

6. **Workflow Registry**
   - Lists available workflows and output formats
   - Gives future plugins and documentation a stable discovery point

## Current Commands

```text
wintersolve scan
wintersolve brain
wintersolve explain
wintersolve debug
wintersolve docs
wintersolve review
```

## Module Rules

Every module should:

- Solve one recognizable developer problem
- Return structured data
- Avoid printing directly
- Avoid hidden network calls
- Include tests
- Handle missing files gracefully

## AI Strategy

WinterSolve should not require AI for its core value. Offline analysis should provide the first answer. AI providers can later improve explanation quality, generate patches, draft docs, and reason over larger context.

## Security Strategy

WinterSolve must be safe to run in private repositories:

- No network calls by default
- Project path access is scoped
- Secret-like values are redacted in reports
- Provider integrations must accept redacted prompts
- JSON output must avoid leaking raw secret values
