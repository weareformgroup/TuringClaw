# TuringClaw Windows Build Script
# Run with: powershell -ExecutionPolicy Bypass -File build_windows.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== TuringClaw Windows Build ===" -ForegroundColor Cyan

# Check Python
Write-Host "Checking Python..."
$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pyCmd) {
    Write-Host "Python not found in PATH" -ForegroundColor Red
    exit 1
}
Write-Host "Python: $($pyCmd.Source)"

# Install PyInstaller
Write-Host "Installing PyInstaller..."
& python -m pip install pyinstaller pillow -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install PyInstaller" -ForegroundColor Red
    exit 1
}

# Build
Write-Host "Building Windows executable..."
$srcDir = "C:\Users\Administrator\TuringClaw"
Set-Location $srcDir

& python -m PyInstaller `
    --name=TuringClaw `
    --windowed `
    --onefile `
    --icon=gui\chinatelecom.jpeg `
    --add-data="gui;gui" `
    --hidden-import=PIL `
    --hidden-import=PIL._imaging `
    --hidden-import=PIL.Image `
    --collect-all=PIL `
    --noconfirm `
    --distpath=dist\windows `
    --workpath=build\windows `
    gui\chat.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build successful!" -ForegroundColor Green
    Write-Host "Executable: dist\windows\TuringClaw.exe"
} else {
    Write-Host "Build failed" -ForegroundColor Red
    exit 1
}
