# Installation

WinterSolve needs Python 3.10 or newer and nothing else. It has two small
runtime dependencies (`typer` and `rich`) and never makes network calls.

## Recommended: pipx

[pipx](https://pipx.pypa.io/) installs the `wintersolve` command in its own
environment and puts it on your PATH:

```bash
pipx install wintersolve
```

Upgrade later with `pipx upgrade wintersolve`.

## pip

```bash
python -m pip install wintersolve
```

Optional extras:

| Extra | Adds | When |
| --- | --- | --- |
| `wintersolve[security]` | Bandit | You want Bandit's Python findings inside `wintersolve brain`. |
| `wintersolve[ai]` | OpenAI and Anthropic SDKs | You are building on the optional provider examples. |
| `wintersolve[dev]` | pytest, ruff, mypy, bandit, pre-commit | You are contributing. |

## Latest development version

```bash
pipx install git+https://github.com/harshitkrhere/WinterSolve.git
```

## From a clone (contributors)

```bash
git clone https://github.com/harshitkrhere/WinterSolve.git
cd WinterSolve
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
wintersolve --version
```

The editable install means code changes take effect immediately.

## Run without installing

From a clone, with no install at all:

```bash
PYTHONPATH=src python -m wintersolve scan .
```

Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"; python -m wintersolve scan .
```

The helper `scripts/wintersolve.ps1` does the same thing; `scripts/install-wintersolve-command.ps1`
registers a `wintersolve` shim for your Windows user account that points at
the clone. Both are conveniences for development, not the supported install path.

## Troubleshooting

**`wintersolve` is not recognized / command not found.**
The install location is not on your PATH. `pipx ensurepath` fixes this for pipx
installs; for pip, `python -m wintersolve ...` always works.

**`python` was not found (Windows).**
Install Python from <https://www.python.org/downloads/> and tick "Add python.exe
to PATH", or use the `py` launcher: `py -m pip install wintersolve`.

**Bandit is slow on my repository.**
Run `wintersolve brain . --no-bandit`. Bandit is only invoked for Python files,
skips virtual environments and dependency folders, and is capped at two minutes.

**The report shows `[id]` style paths oddly in my terminal.**
It should not: reports are printed with terminal markup disabled. If you see
otherwise, please open an issue with the output.
