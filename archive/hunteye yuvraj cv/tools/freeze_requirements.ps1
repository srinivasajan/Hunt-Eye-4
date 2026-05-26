param(
  [string]$PythonExe = "venv\Scripts\python.exe",
  [string]$OutFile = "requirements.lock.txt"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $PythonExe)) {
  throw "Python not found at: $PythonExe"
}

Write-Host "Freezing dependencies -> $OutFile"
& $PythonExe -m pip --version
& $PythonExe -m pip freeze | Out-File -Encoding utf8 $OutFile

Write-Host "Running pip check"
& $PythonExe -m pip check

Write-Host "Done"
