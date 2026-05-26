param(
  [string]$VenvPath = "venv",
  [string]$Python = "py",
  [switch]$Force
)

$ErrorActionPreference = "Stop"

$venvDir = Join-Path (Get-Location) $VenvPath
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if ((Test-Path $venvDir) -and $Force) {
  Remove-Item -Recurse -Force $venvDir
}

if (-not (Test-Path $venvPython)) {
  Write-Host "Creating venv at $venvDir"
  & $Python -m venv $venvDir
}

Write-Host "Upgrading pip"
& $venvPython -m pip install --upgrade pip

if (Test-Path "requirements.txt") {
  Write-Host "Installing requirements.txt"
  & $venvPython -m pip install -r requirements.txt
}

Write-Host "Bootstrap complete"
Write-Host "Run: $venvPython main.py"
