#!/bin/bash
# Build script for macOS

echo "=== AWS End-of-Support Tool - macOS Build ==="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -e .
pip install pyinstaller

# Build the app
echo ""
echo "Building macOS application..."
python -m PyInstaller EndOfSupportTool_mac.spec --clean

# Check if build was successful
if [ -d "dist/EndOfSupportTool.app" ]; then
    echo ""
    echo "=== Build Successful ==="
    echo "Application created at: dist/EndOfSupportTool.app"
    echo ""
    echo "To run the app:"
    echo "  open dist/EndOfSupportTool.app"
    echo ""
    echo "To distribute, you can:"
    echo "  1. Zip the .app bundle: zip -r EndOfSupportTool_mac.zip dist/EndOfSupportTool.app"
    echo "  2. Create a DMG (optional): hdiutil create -volname EndOfSupportTool -srcfolder dist/EndOfSupportTool.app -ov EndOfSupportTool.dmg"
else
    echo ""
    echo "=== Build Failed ==="
    echo "Check the output above for errors"
    exit 1
fi
