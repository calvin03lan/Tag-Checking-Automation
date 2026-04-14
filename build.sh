#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
APP_NAME="Tag_Checking_Automation"
BUNDLE_ID="com.hangseng.tagcheckingautomation"
ICON_FILE="$ROOT_DIR/TAT.ico"
ENTRY_FILE="$ROOT_DIR/main.py"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "[ERROR] Python not found: $PYTHON_BIN"
  echo "Please create the virtual environment first."
  exit 1
fi

if [[ ! -f "$ENTRY_FILE" ]]; then
  echo "[ERROR] Entry file not found: $ENTRY_FILE"
  exit 1
fi

if [[ ! -f "$ICON_FILE" ]]; then
  echo "[WARN] Icon file not found: $ICON_FILE"
  echo "Building without --icon"
  ICON_ARGS=()
else
  ICON_ARGS=(--icon "$ICON_FILE")
fi

if ! "$PYTHON_BIN" -m PyInstaller --version >/dev/null 2>&1; then
  echo "[ERROR] PyInstaller is not installed in .venv"
  echo "Run: $PYTHON_BIN -m pip install pyinstaller"
  exit 1
fi

echo "[INFO] Building $APP_NAME ..."
"$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --clean \
  --onedir \
  --windowed \
  --name "$APP_NAME" \
  --osx-bundle-identifier "$BUNDLE_ID" \
  "${ICON_ARGS[@]}" 
  "$ENTRY_FILE"

echo "[OK] Build complete"
echo "[APP] $ROOT_DIR/dist/${APP_NAME}.app"
echo "[DIR] $ROOT_DIR/dist/${APP_NAME}/"
