@echo off
chcp 65001 >nul
echo Installing PyInstaller and Pillow...
powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList '/c cd /d C:\Users\Administrator\TuringClaw && python -m pip install --user pyinstaller pillow' -Wait -WindowStyle Hidden"
echo Done. Check if packages installed.
python -c "import PyInstaller; print('PyInstaller OK')" 2>nul || echo PyInstaller not found
