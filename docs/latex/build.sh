#!/usr/bin/env bash
set -euo pipefail

# Requirements: pandoc, xelatex (TeXLive), fonts (Noto CJK recommended)

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOCS_DIR="${ROOT_DIR}/.."
OUT_PDF="${ROOT_DIR}/thesis.pdf"

CHAPTERS_FILE="${ROOT_DIR}/chapters.txt"
META_FILE="${ROOT_DIR}/metadata.yaml"

if ! command -v pandoc >/dev/null 2>&1; then
  echo "Error: pandoc not found" >&2; exit 1
fi

if ! command -v xelatex >/dev/null 2>&1; then
  echo "Warning: xelatex not found; pandoc will try anyway" >&2
fi

mapfile -t CHS <"${CHAPTERS_FILE}"

pandoc \
  --from=markdown+yaml_metadata_block+table_captions \
  --to=pdf \
  --pdf-engine=xelatex \
  --metadata-file="${META_FILE}" \
  "${CHS[@]}" \
  -o "${OUT_PDF}"

echo "PDF generated at: ${OUT_PDF}"


