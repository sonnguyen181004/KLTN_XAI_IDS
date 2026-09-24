param(
    [Parameter(Mandatory = $false)]
    [string]$Interface = 'Wi-Fi',
    [Parameter(Mandatory = $false)]
    [string]$Output = 'flows.csv'
)

$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Error 'Missing .venv. Run .\setup.ps1 first.'
    exit 1
}

Write-Host "Capturing CICFlowMeter features on interface: $Interface" -ForegroundColor Cyan
Write-Host "CSV output: $(Join-Path $PSScriptRoot $Output)"
Write-Host 'Browse websites for 1-2 minutes, then press Ctrl+C once to stop and flush flows.'

Push-Location $PSScriptRoot
try {
    & $python (Join-Path $PSScriptRoot 'capture_live.py') --interface $Interface --output $Output
}
finally {
    Pop-Location
}
