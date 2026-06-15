$root = Split-Path -Parent $PSScriptRoot
$installDir = Join-Path $env:LOCALAPPDATA "WinterSolve\bin"
$commandPath = Join-Path $installDir "wintersolve.cmd"
$bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if (Test-Path $bundledPython) {
    $pythonCommand = "`"$bundledPython`""
} else {
    $systemPython = Get-Command python -ErrorAction SilentlyContinue
    $pythonLauncher = Get-Command py -ErrorAction SilentlyContinue

    if ($systemPython) {
        $pythonCommand = "`"$($systemPython.Source)`""
    } elseif ($pythonLauncher) {
        $pythonCommand = "`"$($pythonLauncher.Source)`""
    } else {
        Write-Host "WinterSolve needs Python to install the clean command."
        Write-Host "Install Python, then run this script again:"
        Write-Host ".\scripts\install-wintersolve-command.ps1"
        exit 1
    }
}

New-Item -ItemType Directory -Force -Path $installDir | Out-Null

$command = @"
@echo off
set "PYTHONPATH=$root\src"
$pythonCommand -m wintersolve %*
"@

Set-Content -Path $commandPath -Value $command -Encoding ASCII

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not ($userPath -split ";" | Where-Object { $_ -eq $installDir })) {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$installDir", "User")
}

if (-not ($env:Path -split ";" | Where-Object { $_ -eq $installDir })) {
    $env:Path = "$env:Path;$installDir"
}

Write-Host "Installed WinterSolve command:"
Write-Host "  wintersolve"
Write-Host ""
Write-Host "Run this command now:"
Write-Host "  wintersolve brain ."
