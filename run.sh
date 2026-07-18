#!/usr/bin/env bash
# Run the BDE XBRL Editor from THIS worktree.
# Usage: ./run.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo "-> Creating Python virtual environment ..."
    if command -v python3.13 >/dev/null 2>&1; then
        python3.13 -m venv .venv
    elif [ -x "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13" ]; then
        /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 -m venv .venv
    else
        echo "ERROR: Python 3.13 was not found. Install Python 3.13 and rerun ./run.sh." >&2
        exit 1
    fi
fi

# shellcheck source=/dev/null
source .venv/bin/activate

PY_VERSION="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [ "$PY_VERSION" != "3.13" ]; then
    echo "ERROR: .venv is using Python $PY_VERSION, but this project is configured for Python 3.13." >&2
    echo "Move or remove .venv, then rerun ./run.sh to recreate it with Python 3.13." >&2
    exit 1
fi

echo "-> Installing Python package from $(pwd) ..."
python -m pip install -e ".[dev]" -q

if ! command -v npm >/dev/null 2>&1; then
    echo "ERROR: npm was not found. Install Node.js 20 LTS or newer to use the BDE scraper." >&2
    exit 1
fi

echo "-> Installing BDE scraper runtime dependencies ..."
python -m bde_xbrl_editor.taxonomy_catalog.scraper --setup-only

echo "-> Clearing stale pycache ..."
find src -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "-> Launching BDE XBRL Editor ..."
python -m bde_xbrl_editor
