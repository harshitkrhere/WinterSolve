param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $Args
)

$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $root "src"

$systemPython = Get-Command python -ErrorAction SilentlyContinue
if ($systemPython) {
    & $systemPython.Source -m wintersolve @Args
    exit $LASTEXITCODE
}

$pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pythonLauncher) {
    & $pythonLauncher.Source -m wintersolve @Args
    exit $LASTEXITCODE
}

Write-Host "WinterSolve needs Python to run, but Python was not found."
Write-Host "Install Python from https://www.python.org/downloads/ and then run this command again:"
Write-Host ".\scripts\wintersolve.ps1 scan ."
exit 1
