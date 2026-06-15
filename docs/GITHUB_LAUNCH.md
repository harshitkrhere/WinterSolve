# GitHub Launch Guide

This guide explains how developers can use WinterSolve after the project is pushed to GitHub.

## Install From GitHub

Before WinterSolve is published to PyPI, users can install it directly from the GitHub repository:

```powershell
python -m pip install git+https://github.com/harshitkrhere/WinterSolve.git
```

After installation:

```powershell
wintersolve brain .
```

Repository: `https://github.com/harshitkrhere/WinterSolve.git`

## Use WinterSolve Inside Any Project

WinterSolve is designed to be run from inside another codebase.

Example for a website:

```powershell
cd my-react-website
wintersolve brain .
```

Example for an app:

```powershell
cd my-mobile-app
wintersolve brain . --format markdown --output wintersolve-report.md
```

Example for an API:

```powershell
cd my-api-service
wintersolve scan .
wintersolve docs .
wintersolve review .
```

## What Developers Get

The flagship command is:

```powershell
wintersolve brain .
```

It creates a Repo Brain report with:

- Project identity
- Languages and stack
- Source and test layout
- Architecture map
- Detected setup/test/build commands
- Documentation health
- Security and privacy notes
- Risks, recommendations, and next actions

## Use JSON Output In Apps, Websites, And IDEs

WinterSolve can produce stable JSON for tools:

```powershell
wintersolve brain . --format json --output wintersolve-report.json
```

Other projects can read that JSON to show Repo Brain data in:

- VS Code extensions
- Web dashboards
- Internal developer portals
- CI reports
- Documentation sites
- Project onboarding pages

## Use In GitHub Actions

Example workflow step:

```yaml
- name: Install WinterSolve
  run: python -m pip install git+https://github.com/harshitkrhere/WinterSolve.git

- name: Generate Repo Brain report
  run: wintersolve brain . --format markdown --output wintersolve-report.md
```

## Recommended Launch Checklist

Before announcing WinterSolve:

- Push the repository to GitHub.
- Confirm the GitHub repository URL is correct in the README and launch docs.
- Add screenshots or copied sample output from `wintersolve brain .`.
- Add repository topics such as `developer-tools`, `ai`, `cli`, `open-source`, and `codebase-analysis`.
- Create the first release tag, such as `v0.1.0`.
- Add a short demo GIF or terminal recording later.
