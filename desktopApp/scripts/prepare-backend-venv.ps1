param(
  [string]$BackendRoot = (Join-Path $PSScriptRoot "..\resources\backend")
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackendRoot)) {
  throw "Backend staging directory not found: $BackendRoot. Run npm run stage:backend first."
}

$requirements = Join-Path $BackendRoot "requirements.txt"
if (-not (Test-Path $requirements)) {
  throw "requirements.txt not found in $BackendRoot"
}

$venvPath = Join-Path $BackendRoot ".venv"
$pythonExe = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
  Write-Host "Creating bundled backend virtual environment..."
  python -m venv $venvPath
}

Write-Host "Installing backend dependencies into bundled venv..."
& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r $requirements

Write-Host "Backend runtime ready at $pythonExe"
