# TuringClaw 启动脚本 — 一键启动所有服务
# 用法: powershell -ExecutionPolicy Bypass -File start_turingclaw.ps1

$ErrorActionPreference = "Continue"
$tcRoot = "C:\Users\Administrator\TuringClaw"

# 1. 启动 LM Studio (本地 GPU 推理)
Write-Host "[1/3] 启动 LM Studio..." -ForegroundColor Cyan
$lmsExe = "C:\Users\Administrator\AppData\Local\lm-studio\.bundle\lms.exe"
if(Test-Path $lmsExe){
    & $lmsExe server start 2>&1 | Out-Null
    Start-Sleep 2
    try { Invoke-WebRequest -Uri "http://localhost:1234/v1/models" -TimeoutSec 5 | Out-Null; Write-Host "  [OK] LM Studio (port 1234)" -ForegroundColor Green }
    catch { Write-Host "  [FAIL] LM Studio 未启动" -ForegroundColor Red }
} else { Write-Host "  [SKIP] LM Studio 未安装" -ForegroundColor Yellow }

# 2. 启动 GBrain (知识库)
Write-Host "[2/3] 启动 GBrain..." -ForegroundColor Cyan
$gbrainExe = "C:\Users\Administrator\.bun\bin\gbrain.exe"
if(Test-Path $gbrainExe){
    try { Invoke-WebRequest -Uri "http://localhost:8484/health" -TimeoutSec 3 | Out-Null; Write-Host "  [OK] GBrain 已在运行" -ForegroundColor Green }
    catch {
        Start-Process -FilePath $gbrainExe -ArgumentList "serve", "--http", "--port", "8484" -WindowStyle Hidden
        Start-Sleep 6
        try { Invoke-WebRequest -Uri "http://localhost:8484/health" -TimeoutSec 5 | Out-Null; Write-Host "  [OK] GBrain (port 8484)" -ForegroundColor Green }
        catch { Write-Host "  [FAIL] GBrain 未启动" -ForegroundColor Red }
    }
} else { Write-Host "  [SKIP] GBrain 未安装" -ForegroundColor Yellow }

# 3. 启动 TuringClaw GUI
Write-Host "[3/3] 启动 TuringClaw GUI..." -ForegroundColor Cyan
$py = "C:\Program Files\QClaw\v0.2.35.624\resources\python\python.exe"
$env:PYTHONPATH = $tcRoot
$env:PYTHONIOENCODING = "utf-8"
$env:CUDA_VISIBLE_DEVICES = ""
$env:OLLAMA_NUM_GPU = "0"
if(Test-Path "$tcRoot\gui\chat.py"){
    Start-Process -FilePath $py -ArgumentList "gui/chat.py" -WorkingDirectory $tcRoot
    Write-Host "  [OK] TuringClaw GUI 已启动" -ForegroundColor Green
} else { Write-Host "  [FAIL] gui/chat.py 不存在" -ForegroundColor Red }

Write-Host ""
Write-Host "=== 启动完成 ===" -ForegroundColor Cyan
Write-Host "LM Studio:  http://localhost:1234"
Write-Host "GBrain:     http://localhost:8484"
Write-Host "TuringClaw GUI 已打开"
