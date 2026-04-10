#!/usr/bin/env bash
# Run the BDE XBRL Editor from THIS worktree, always with a clean install.
# Usage: ./run.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "→ Installing from $(pwd) …"
pip install -e ".[dev]" -q

echo "→ Clearing stale pycache …"
find src -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "→ Launching BDE XBRL Editor …"
python -m bde_xbrl_editor
