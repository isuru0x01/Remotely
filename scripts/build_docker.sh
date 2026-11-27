#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "========================================================"
echo "Building Windows .exe using Docker (Wine)..."
echo "Project Root: $PROJECT_ROOT"
echo "========================================================"

# Run builder container mounting workspace root
# Compiles targeted scripts and fixes host user permissions
docker run --rm \
    -v "$PROJECT_ROOT:/src" \
    cdrx/pyinstaller-windows:python3 \
    "python scripts/build.py && chown -R $(id -u):$(id -g) dist build"

echo "========================================================"
echo "[OK] Build complete! Executables available in dist/"
echo "========================================================"
