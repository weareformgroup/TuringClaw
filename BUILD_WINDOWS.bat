@echo off
chcp 65001 >nul
echo =============================================
echo   TuringClaw GUI - Windows Build Script
echo =============================================
echo.

REM Create local packages directory
echo [1/4] Creating local packages directory...
if not exist "packages" mkdir packages
set PYTHONUSERBASE=%CD%\packages
echo   Done. Packages will be installed to: %CD%\packages
echo.

REM Install dependencies
echo [2/4] Installing dependencies (pyinstaller, pillow)...
echo   This may take a few minutes...
python -m pip install --user --ignore-installed pyinstaller pillow 2>nul
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install dependencies.
    echo.
    echo Please try running this script as Administrator, OR:
    echo 1. Open CMD as Admin
    echo 2. cd C:\Users\Administrator\TuringClaw
    echo 3. python -m pip install pyinstaller pillow
    pause
    exit /b 1
)
echo   Dependencies installed!
echo.

REM Build
echo [3/4] Building Windows executable...
echo   Running PyInstaller...
if not exist "dist" mkdir dist
if not exist "dist\windows" mkdir dist\windows

python -m PyInstaller ^
    --name=TuringClaw ^
    --windowed ^
    --onefile ^
    --icon=gui\chinatelecom.jpeg ^
    --add-data="gui;gui" ^
    --hidden-import=PIL ^
    --hidden-import=PIL._imaging ^
    --hidden-import=PIL.Image ^
    --collect-all=PIL ^
    --noconfirm ^
    --distpath=dist\windows ^
    --workpath=build\windows ^
    gui\chat.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo [4/4] Build complete!
echo.
echo =============================================
echo   BUILD SUCCESSFUL!
echo =============================================
echo.
echo Executable location:
echo   dist\windows\TuringClaw.exe
echo.
echo To run: Double-click dist\windows\TuringClaw.exe
echo.
pause
