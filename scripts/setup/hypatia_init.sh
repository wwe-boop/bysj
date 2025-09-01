#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")"/../.. && pwd)"
cd "$ROOT_DIR"

if [ ! -d hypatia ]; then
  echo "[INFO] Creating hypatia directory placeholder (submodule stubs)."
  mkdir -p hypatia
fi

echo "[INFO] Initialize or update submodules if configured..."
git submodule update --init --recursive || true

echo "[INFO] Hypatia placeholder is ready. Please follow docs/hypatia_setup.md to install full dependencies."

