@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Starting TuringClaw GUI...
python gui\chat.py
pause
