# Runs WinterSolve from this clone without installing it. Development helper;
# the supported install is `pipx install wintersolve` (see docs/INSTALLATION.md).
#
#   .\scripts\wintersolve.ps1 brain .

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $Args
)

$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $root "src"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    Write-Host "Python was not found. Install it from https://www.python.org/downloads/ and try again."
    exit 1
}

& $python.Source -m wintersolve @Args
exit $LASTEXITCODE
