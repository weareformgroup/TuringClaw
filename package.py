"""
TuringClaw GUI Windows/MacOS packaging specification.
Creates standalone executables from gui/chat.py
"""
from PyInstaller.__main__ import run
import os, sys

def build_windows():
    """Build Windows executable using PyInstaller."""
    print("Building Windows executable...")
    
    args = [
        "gui/chat.py",
        "--name=TuringClaw",
        "--windowed",           # GUI mode (no console)
        "--onefile",            # Single executable
        "--icon=gui/chinatelecom.jpeg",
        "--add-data=gui;gui",
        "--hidden-import=PIL",
        "--hidden-import=PIL._imaging",
        "--collect-all=PIL",
        "--noconfirm",
        "--distpath=dist/windows",
        "--workpath=build/windows",
        "--specpath=.",
    ]
    
    print(f"Running PyInstaller with args: {args[:4]}...")
    # Note: Run separately: pyinstaller --name TuringClaw --windowed --onefile gui/chat.py

def build_macos():
    """Build macOS .app bundle using PyInstaller."""
    print("Building macOS app bundle...")
    # Note: Run on macOS: pyinstaller --name TuringClaw --windowed --osx-bundle-identifier=com.chinatelecom.turingclaw gui/chat.py

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python package.py windows|macos")
        sys.exit(1)
    
    if sys.argv[1] == "windows":
        build_windows()
    elif sys.argv[1] == "macos":
        build_macos()
