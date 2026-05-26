param(
  [string]$PythonExe = "venv\Scripts\python.exe",
  [string]$Name = "HuntEye",
  [string]$Entry = "main.py",
  [switch]$OneFile
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $PythonExe)) {
  throw "Python not found at: $PythonExe"
}

Write-Host "Installing build deps (pyinstaller)"
& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install pyinstaller

$onefileFlag = @()
if ($OneFile) { $onefileFlag = @("--onefile") }

Write-Host "Building $Name from $Entry"

# Build with PyInstaller
& $PythonExe -m PyInstaller --noconfirm --clean @onefileFlag --name $Name $Entry

# Ensure config.yaml is shipped next to the exe (and accessible at runtime)
if ($OneFile) {
  Copy-Item -Force "config.yaml" -Destination "dist\config.yaml"
} else {
  Copy-Item -Force "config.yaml" -Destination (Join-Path "dist" $Name)
}

Write-Host "Build complete. See dist\\$Name\\ (or dist\\$Name.exe in --onefile mode)."
