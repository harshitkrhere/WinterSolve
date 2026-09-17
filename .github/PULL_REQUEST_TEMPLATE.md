## Summary

What changed and why. Link the issue if there is one.

## Verification

```text
ruff check . && ruff format --check . && mypy && pytest
```

Anything you checked by hand (for example, the report on a real repository).

## Checklist

- [ ] Solves a clear developer problem or fixes a real bug.
- [ ] Tests added or updated (temp-directory fixtures, no network).
- [ ] Docs updated if user-facing behaviour changed (README, docs/COMMANDS.md).
- [ ] CHANGELOG.md has an entry under "Unreleased".
- [ ] No hidden network calls; secret-like values stay redacted.
