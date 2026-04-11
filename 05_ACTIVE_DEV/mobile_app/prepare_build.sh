#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────
# Aurexis Core — M9 Build Preparation
#
# Copies the aurexis_lang source package into mobile_app/
# so Buildozer can find and bundle it in the APK.
#
# Run this from mobile_app/ BEFORE running buildozer:
#   bash prepare_build.sh
# ──────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Source location (relative to mobile_app/)
SRC="../aurexis_lang/src/aurexis_lang"

if [ ! -d "$SRC" ]; then
    echo "ERROR: Cannot find aurexis_lang source at $SRC"
    echo "Make sure you're running this from mobile_app/"
    exit 1
fi

# Clean previous copy
rm -rf ./aurexis_lang
mkdir -p ./aurexis_lang/src

# Copy the package
echo "Copying aurexis_lang source..."
cp -r "$SRC" ./aurexis_lang/src/aurexis_lang

# Count files
COUNT=$(find ./aurexis_lang/src/aurexis_lang -name "*.py" | wc -l)
echo "Copied $COUNT Python files."

# Remove __pycache__ directories (they cause build issues)
find ./aurexis_lang -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "Done. Ready to build."
echo ""
echo "Next: buildozer -v android debug"
