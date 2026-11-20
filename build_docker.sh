#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================"
echo "Building Windows .exe using Docker..."
echo "========================================================"

# Run builder container mounting current workspace
# Compiles all scripts in src/ and fixes permissions to the host user
docker run --rm \
    -v "$SCRIPT_DIR:/src" \
    cdrx/pyinstaller-windows:python3 \
    "python build.py && chown -R $(id -u):$(id -g) dist build"

echo "========================================================"
echo "[OK] Build complete! Executables available in dist/"
echo "========================================================"
