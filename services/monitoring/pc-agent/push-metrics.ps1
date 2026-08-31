<#
    push-metrics.ps1 - Start the metric push agent on Windows (native, no WSL).
    Pushes system metrics to the Halo's Pushgateway.

    Usage:  .\push-metrics.ps1 [config.yaml]
#>
param(
    [string]$Config
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Config) { $Config = Join-Path $ScriptDir "config.yaml" }
$VenvDir = Join-Path $ScriptDir ".venv"

function Find-Python {
    foreach ($cmd in @("py -3", "python", "python3")) {
        $parts = $cmd.Split(" ")
        if (Get-Command $parts[0] -ErrorAction SilentlyContinue) { return $cmd }
    }
    throw "Python 3 not found. Install from https://www.python.org/downloads/ or 'winget install Python.Python.3.12'."
}

$Python = Find-Python

if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating virtual environment..."
    Invoke-Expression "$Python -m venv `"$VenvDir`""
}

$VenvPy = Join-Path $VenvDir "Scripts\python.exe"

& $VenvPy -c "import psutil" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing dependencies..."
    & $VenvPy -m pip install -r (Join-Path $ScriptDir "requirements.txt")
}

Write-Host "Starting metric agent (config: $Config)..."
& $VenvPy (Join-Path $ScriptDir "agent.py") -c $Config
