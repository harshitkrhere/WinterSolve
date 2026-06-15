# Installing WinterSolve

WinterSolve should be used with the clean command prefix:

```powershell
wintersolve brain .
wintersolve scan .
wintersolve explain src/wintersolve/cli.py
```

## Option 1: Install the Clean Windows Command

From the project folder:

```powershell
.\scripts\install-wintersolve-command.ps1
```

Open a new PowerShell window, then run:

```powershell
wintersolve brain .
```

This creates a local `wintersolve` command for your Windows user account.

## Option 2: Editable Python Install

If Python and pip are installed:

```powershell
python -m pip install -e .
wintersolve brain .
```

## Development Fallback: PowerShell Helper

From the project folder:

```powershell
.\scripts\wintersolve.ps1 scan .
```

This helper is only for development fallback. Public docs and examples should use `wintersolve <command>`.

## Development Fallback: Python Module

If Python is installed:

```powershell
$env:PYTHONPATH="src"; python -m wintersolve scan .
```

## Common Problems

### Python was not found

Install Python from the official Python website, or run `.\scripts\install-wintersolve-command.ps1` if you are running WinterSolve inside Codex.

### `wintersolve` is not recognized

The command has not been installed into your shell path yet. Run:

```powershell
.\scripts\install-wintersolve-command.ps1
```

Then open a new PowerShell window.
