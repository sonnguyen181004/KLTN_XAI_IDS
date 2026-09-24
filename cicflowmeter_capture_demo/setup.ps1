# Run this file once in an Administrator PowerShell after installing Python 3.14.
$ErrorActionPreference = 'Stop'

Write-Host 'Creating isolated Python 3.14 environment...'
py -3.14 -m venv .venv

$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')

Write-Host ''
Write-Host 'Setup complete. Run .\capture.ps1 -Interface "Wi-Fi" next.' -ForegroundColor Green
