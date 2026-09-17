# Registers a `wintersolve` command for the current Windows user that runs this
# clone directly (no pip install). Useful while developing. The supported install
# for everyone else is `pipx install wintersolve`; see docs/INSTALLATION.md.

$root = Split-Path -Parent $PSScriptRoot
$installDir = Join-Path $env:LOCALAPPDATA "WinterSolve\bin"
$commandPath = Join-Path $installDir "wintersolve.cmd"

$python = Get-Command python -ErrorAction SilentlyContinue
$launcher = Get-Command py -ErrorAction SilentlyContinue

if ($python) {
    $pythonCommand = "`"$($python.Source)`""
} elseif ($launcher) {
    $pythonCommand = "`"$($launcher.Source)`""
} else {
    Write-Host "Python was not found. Install it from https://www.python.org/downloads/ (tick 'Add python.exe to PATH'),"
    Write-Host "then run this script again."
    exit 1
}

New-Item -ItemType Directory -Force -Path $installDir | Out-Null

$shim = @"
@echo off
set "PYTHONPATH=$root\src"
$pythonCommand -m wintersolve %*
"@

Set-Content -Path $commandPath -Value $shim -Encoding ASCII

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not (($userPath -split ";") -contains $installDir)) {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$installDir", "User")
}
if (-not (($env:Path -split ";") -contains $installDir)) {
    $env:Path = "$env:Path;$installDir"
}

Write-Host "Installed a development shim at $commandPath"
Write-Host "Open a new terminal and try:"
Write-Host "  wintersolve brain ."
