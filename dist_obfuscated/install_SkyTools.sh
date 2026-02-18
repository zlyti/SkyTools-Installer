#!/bin/bash

# SkyTools Installer for Linux

REPO="zlyti/SkyTools-Installer"
ZIP_NAME="SkyTools_Protected.zip"
RELEASE_URL="https://github.com/$REPO/releases/latest/download/$ZIP_NAME"
INSTALL_PATH="$HOME/.local/share/SkyTools_Setup"

echo "☁️ SkyTools Installer | .gg/skytools"

# 1. Clean Setup Directory
if [ -d "$INSTALL_PATH" ]; then
    rm -rf "$INSTALL_PATH"
fi
mkdir -p "$INSTALL_PATH"

# 2. Download SkyTools
echo "⬇️ Downloading SkyTools..."
if command -v curl >/dev/null 2>&1; then
    curl -L -o "$INSTALL_PATH/$ZIP_NAME" "$RELEASE_URL"
elif command -v wget >/dev/null 2>&1; then
    wget -O "$INSTALL_PATH/$ZIP_NAME" "$RELEASE_URL"
else
    echo "❌ Error: Neither curl nor wget found. Please install one of them."
    exit 1
fi

if [ ! -f "$INSTALL_PATH/$ZIP_NAME" ]; then
    echo "❌ Failed to download SkyTools. Check your internet connection."
    exit 1
fi

# 3. Extract
echo "📦 Extracting files..."
unzip -o "$INSTALL_PATH/$ZIP_NAME" -d "$INSTALL_PATH" > /dev/null
rm "$INSTALL_PATH/$ZIP_NAME"

# 4. Check for Python
echo "🐍 Checking for Python..."
PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "❌ Python not found. Please install Python 3 (e.g., sudo apt install python3)."
    exit 1
fi

# Verify Python version (optional, but good practice)
$PYTHON_CMD --version

# 5. Run Python Installer
INSTALLER_SCRIPT="$INSTALL_PATH/src/installer.py"

if [ -f "$INSTALLER_SCRIPT" ]; then
    echo "🚀 Running SkyTools Installer..."
    $PYTHON_CMD "$INSTALLER_SCRIPT"
else
    echo "⚠️ Installer script not found at standard path. Searching..."
    FOUND_SCRIPT=$(find "$INSTALL_PATH" -name "installer.py" | head -n 1)
    if [ -n "$FOUND_SCRIPT" ]; then
        echo "🚀 Found at $FOUND_SCRIPT, running..."
        $PYTHON_CMD "$FOUND_SCRIPT"
    else
        echo "❌ Fatal: Could not find installer.py"
        exit 1
    fi
fi

echo "✅ Installation process finished."
