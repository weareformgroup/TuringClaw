#!/usr/bin/env python3
"""
Build TuringClaw executables for Windows and macOS.
Usage: python build.py windows
       python build.py macos
"""
import os, sys, subprocess, shutil, platform

def ensure_deps():
    """Ensure pyinstaller and pillow are available."""
    try:
        import PyInstaller
        from PIL import Image
        print("[OK] Dependencies already installed")
        return True
    except ImportError:
        print("[INFO] Installing dependencies...")
        # Try user install
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user",
             "pyinstaller", "pillow"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("[OK] Dependencies installed")
            return True
        print(f"[ERROR] Failed: {result.stderr[:200]}")
        return False

def build_windows():
    """Build Windows single-file executable."""
    print("\n=== Building Windows Executable ===")
    if not ensure_deps():
        return False
    
    os.makedirs("dist/windows", exist_ok=True)
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=TuringClaw",
        "--windowed",
        "--onefile",
        "--icon=gui\\chinatelecom.jpeg",
        "--add-data=gui;gui",
        "--hidden-import=PIL",
        "--hidden-import=PIL._imaging",
        "--hidden-import=PIL.Image",
        "--collect-all=PIL",
        "--noconfirm",
        "--distpath=dist/windows",
        "--workpath=build/windows",
        "--specpath=.",
        "gui\\chat.py",
    ]
    
    print(f"Running: {' '.join(cmd[:5])}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("\n[SUCCESS] Windows executable built!")
        print("Location: dist/windows/TuringClaw.exe")
        return True
    else:
        print(f"[ERROR] Build failed:\n{result.stderr[-500:]}")
        return False

def build_macos():
    """Build macOS .app bundle."""
    print("\n=== Building macOS Application ===")
    if not ensure_deps():
        return False
    
    os.makedirs("dist/macos", exist_ok=True)
    
    cmd = [
        "python3", "-m", "PyInstaller",
        "--name=TuringClaw",
        "--windowed",
        "--icon=gui/chinatelecom.jpeg",
        "--add-data=gui:gui",
        "--hidden-import=PIL",
        "--hidden-import=PIL._imaging",
        "--hidden-import=PIL.Image",
        "--collect-all=PIL",
        "--noconfirm",
        "--distpath=dist/macos",
        "--workpath=build/macos",
        "--specpath=.",
        "gui/chat.py",
    ]
    
    print(f"Running: {' '.join(cmd[:5])}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("\n[SUCCESS] macOS app built!")
        print("Location: dist/macos/TuringClaw.app")
        return True
    else:
        print(f"[ERROR] Build failed:\n{result.stderr[-500:]}")
        return False

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    target = sys.argv[1].lower() if len(sys.argv) > 1 else platform.system().lower()
    
    print(f"Building for: {target}")
    
    if "win" in target:
        ok = build_windows()
    elif "darwin" in target or "mac" in target:
        ok = build_macos()
    else:
        print("Usage: python build.py windows|macos")
        sys.exit(1)
    
    sys.exit(0 if ok else 1)
