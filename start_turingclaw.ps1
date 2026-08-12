# TuringClaw 启动脚本 v3 — 2026-08-13
# 修复：延迟启动 + 重试 + 日志
# 用法: powershell -ExecutionPolicy Bypass -File start_turingclaw.ps1
# 自启: Windows 启动文件夹 TuringClaw Startup.lnk

$ErrorActionPreference = "Continue"
$tcRoot = "C:\Users\Administrator\TuringClaw"
$logFile = "$tcRoot\startup.log"

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
}

Write-Log "=== TuringClaw Startup ==="

# 等待 60 秒让系统稳定（登录后不要立刻启动）
Write-Log "Waiting 60s for system to stabilize..."
Start-Sleep 60

# === 环境变量 ===
$env:PATH = "C:\Users\Administrator\.bun\bin;$env:PATH"
$env:CUDA_VISIBLE_DEVICES = ""
$env:LLAMA_SERVER_BASE_URL = "http://localhost:1234/v1"
$env:LLAMA_SERVER_API_KEY = "***"
$env:PYTHONIOENCODING = "utf-8"
Remove-Item Env:\OLLAMA_BASE_URL -ErrorAction SilentlyContinue

# === 1. LM Studio ===
Write-Log "[1/3] LM Studio..."
$lmsExe = "C:\Users\Administrator\AppData\Local\lm-studio\.bundle\lms.exe"
if (Test-Path $lmsExe) {
    $started = $false
    for ($i = 1; $i -le 6; $i++) {
        try {
            Invoke-WebRequest -Uri "http://localhost:1234/v1/models" -TimeoutSec 5 | Out-Null
            $started = $true; break
        } catch {
            Write-Log "  Attempt $i/6: starting lms.exe..."
            & $lmsExe server start 2>&1 | Out-Null
            Start-Sleep 10
        }
    }
    if ($started) { Write-Log "  [OK] LM Studio running (port 1234)" }
    else { Write-Log "  [FAIL] LM Studio not responding after 6 attempts" }
} else { Write-Log "  [SKIP] lms.exe not found" }

# === 2. GBrain ===
Write-Log "[2/3] GBrain..."
$gbOk = $false
try {
    Invoke-WebRequest -Uri "http://localhost:8484/health" -TimeoutSec 3 | Out-Null
    $gbOk = $true
} catch {}
if (-not $gbOk) {
    $bunExe = "C:\Users\Administrator\.bun\bin\bun.exe"
    if (Test-Path $bunExe) {
        for ($i = 1; $i -le 3; $i++) {
            Write-Log "  Attempt $i/3: starting GBrain..."
            Start-Process -FilePath $bunExe `
                -ArgumentList "C:\Users\Administrator\gbrain\src\cli.ts", "serve", "--http", "--port", "8484" `
                -WindowStyle Hidden -WorkingDirectory "C:\Users\Administrator\gbrain"
            Start-Sleep 10
            try {
                Invoke-WebRequest -Uri "http://localhost:8484/health" -TimeoutSec 5 | Out-Null
                $gbOk = $true; break
            } catch {}
        }
    }
}
if ($gbOk) { Write-Log "  [OK] GBrain running (port 8484)" }
else { Write-Log "  [FAIL] GBrain not responding" }

# === 3. TuringClaw GUI (optional) ===
Write-Log "[3/3] TuringClaw GUI..."
$py = "C:\Program Files\QClaw\v0.2.35.624\resources\python\python.exe"
$env:PYTHONPATH = $tcRoot
if (Test-Path "$tcRoot\gui\chat.py") {
    $sessionName = [System.Environment]::GetEnvironmentVariable("SESSIONNAME")
    if ($sessionName -or $env:USERINTERACTIVE) {
        Start-Process -FilePath $py -ArgumentList "gui/chat.py" -WorkingDirectory $tcRoot
        Write-Log "  [OK] GUI started"
    } else {
        Write-Log "  [SKIP] headless session"
    }
} else { Write-Log "  [SKIP] gui/chat.py not found" }

Write-Log "=== Startup complete ==="
Write-Log "LM Studio:  http://localhost:1234"
Write-Log "GBrain:     http://localhost:8484"
Write-Log "Log file:   $logFile"
