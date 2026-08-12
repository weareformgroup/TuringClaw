# TuringClaw 启动脚本 v2 — 2026-08-10 重写
# 用法: powershell -ExecutionPolicy Bypass -File start_turingclaw.ps1
# 也可作为 Windows 任务计划程序的开机自启脚本

$ErrorActionPreference = "Continue"
$tcRoot = "C:\Users\Administrator\TuringClaw"

# === 环境变量 ===
$env:PATH = "C:\Users\Administrator\.bun\bin;$env:PATH"
$env:CUDA_VISIBLE_DEVICES = ""
$env:LLAMA_SERVER_BASE_URL = "http://localhost:1234/v1"
$env:LLAMA_SERVER_API_KEY = "lm-studio"
$env:PYTHONIOENCODING = "utf-8"
Remove-Item Env:\OLLAMA_BASE_URL -ErrorAction SilentlyContinue

# === 1. LM Studio ===
Write-Host "[1/3] LM Studio..." -ForegroundColor Cyan
$lmsExe = "C:\Users\Administrator\AppData\Local\lm-studio\.bundle\lms.exe"
if (Test-Path $lmsExe) {
    try { Invoke-WebRequest -Uri "http://localhost:1234/v1/models" -TimeoutSec 3 | Out-Null; Write-Host "  [OK] already running" -ForegroundColor Green }
    catch {
        & $lmsExe server start 2>&1 | Out-Null
        # 等待最多 30 秒，每 5 秒检查一次
        $maxRetries = 6
        $started = $false
        for ($i = 1; $i -le $maxRetries; $i++) {
            Start-Sleep 5
            try { Invoke-WebRequest -Uri "http://localhost:1234/v1/models" -TimeoutSec 5 | Out-Null; $started = $true; break } catch {}
            Write-Host "  Waiting for LM Studio... ($i/$maxRetries)"
        }
        if ($started) { Write-Host "  [OK] started (port 1234)" -ForegroundColor Green }
        else { Write-Host "  [FAIL] LM Studio not responding after 30s" -ForegroundColor Red }
    }
} else { Write-Host "  [SKIP] lms.exe not found" -ForegroundColor Yellow }

# === 2. GBrain ===
Write-Host "[2/3] GBrain..." -ForegroundColor Cyan
try { Invoke-WebRequest -Uri "http://localhost:8484/health" -TimeoutSec 3 | Out-Null; Write-Host "  [OK] already running" -ForegroundColor Green }
catch {
    $bunExe = "C:\Users\Administrator\.bun\bin\bun.exe"
    if (Test-Path $bunExe) {
        Start-Process -FilePath $bunExe `
            -ArgumentList "C:\Users\Administrator\gbrain\src\cli.ts", "serve", "--http", "--port", "8484" `
            -WindowStyle Hidden `
            -WorkingDirectory "C:\Users\Administrator\gbrain"
        Start-Sleep 8
        try { Invoke-WebRequest -Uri "http://localhost:8484/health" -TimeoutSec 5 | Out-Null; Write-Host "  [OK] started (port 8484)" -ForegroundColor Green }
        catch { Write-Host "  [FAIL] GBrain not responding" -ForegroundColor Red }
    } else { Write-Host "  [SKIP] bun.exe not found" -ForegroundColor Yellow }
}

# === 3. TuringClaw GUI (optional, only if desktop session) ===
Write-Host "[3/3] TuringClaw GUI..." -ForegroundColor Cyan
$py = "C:\Program Files\QClaw\v0.2.35.624\resources\python\python.exe"
$env:PYTHONPATH = $tcRoot
if (Test-Path "$tcRoot\gui\chat.py") {
    # Only start GUI if not running as SYSTEM (task scheduler) or headless
    $sessionName = [System.Environment]::GetEnvironmentVariable("SESSIONNAME")
    if ($sessionName -or $env:USERINTERACTIVE) {
        Start-Process -FilePath $py -ArgumentList "gui/chat.py" -WorkingDirectory $tcRoot
        Write-Host "  [OK] GUI started" -ForegroundColor Green
    } else {
        Write-Host "  [SKIP] headless/session, GUI not started" -ForegroundColor Yellow
    }
} else { Write-Host "  [SKIP] gui/chat.py not found" -ForegroundColor Yellow }

Write-Host ""
Write-Host "=== Startup complete ===" -ForegroundColor Cyan
Write-Host "LM Studio:  http://localhost:1234"
Write-Host "GBrain:     http://localhost:8484"
