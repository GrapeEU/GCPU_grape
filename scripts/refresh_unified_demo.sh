#!/bin/bash
set -euo pipefail

# Refresh the unified repository with the GCPU demo knowledge graph.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
KG_DIR="$ROOT_DIR/kg_example/GCPU_demo"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || command -v python || true)}"

if [ -z "$PYTHON_BIN" ]; then
  echo "[ERROR] Aucun interpréteur Python3/Python trouvé dans le PATH." >&2
  exit 1
fi

echo "[INFO] Clearing 'unified' repository..."
"$PYTHON_BIN" "$ROOT_DIR/scripts/kg_clean.py" unified "$@"

echo "[INFO] Loading demo files from $KG_DIR ..."
"$PYTHON_BIN" "$ROOT_DIR/scripts/kg_load_dir.py" "$KG_DIR" unified "$@"

echo "[OK] Unified repository refreshed with GCPU demo data."
