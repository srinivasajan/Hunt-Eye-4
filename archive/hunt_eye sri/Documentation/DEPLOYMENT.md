# Deployment Runtime (Dev 1.1)

This repo supports a repeatable Windows build and dependency-freeze workflow.

## 1) Bootstrap

- Create venv + install deps:
  - `powershell -ExecutionPolicy Bypass -File tools/bootstrap.ps1`

## 2) Freeze dependencies

- Generates a lock file:
  - `powershell -ExecutionPolicy Bypass -File tools/freeze_requirements.ps1`

Outputs: `requirements.lock.txt`

## 3) Build a Windows executable

- Build with PyInstaller:
  - `powershell -ExecutionPolicy Bypass -File tools/build.ps1`

Notes:
- Build output is under `dist/`.
- `config.yaml` is bundled next to the executable output.

## 4) CI builds

A GitHub Actions workflow builds a Windows artifact on pushes to `main` and tags.
See `.github/workflows/build-windows.yml`.
