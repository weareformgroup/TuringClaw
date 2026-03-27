#!/bin/bash
# TuringClaw GUI - macOS Build Script
# Run with: chmod +x build_macos.sh && ./build_macos.sh

set -e

echo "============================================="
echo "  TuringClaw GUI - macOS Build Script"
echo "============================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Install from python.org"
    exit 1
fi

echo "[1/4] Checking Python: $(python3 --version)"

# Install dependencies
echo ""
echo "[2/4] Installing dependencies (pyinstaller, pillow)..."
python3 -m pip install pyinstaller pillow --user
echo "   Done."

# Create dist directory
mkdir -p dist/macos

# Build
echo ""
echo "[3/4] Building macOS application..."
echo "   Running PyInstaller..."

python3 -m PyInstaller \
    --name=TuringClaw \
    --windowed \
    --onefile \
    --icon=gui/chinatelecom.jpeg \
    --add-data="gui:gui" \
    --hidden-import=PIL \
    --hidden-import=PIL._imaging \
    --hidden-import=PIL.Image \
    --collect-all=PIL \
    --noconfirm \
    --distpath=dist/macos \
    --workpath=build/macos \
    gui/chat.py

echo ""
echo "[4/4] Build complete!"
echo ""
echo "============================================="
echo "  BUILD SUCCESSFUL!"
echo "============================================="
echo ""
echo "Application location:"
echo "   dist/macos/TuringClaw"
echo ""
echo "To run: open dist/macos/TuringClaw.app"
echo "To create disk image: use the Finder to compress or use hdiutil"
echo ""
