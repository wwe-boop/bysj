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

# 兼容 macOS 自带 bash (无 mapfile)，并切换到脚本目录以保证相对路径正确
CHS_ARGS=$(awk 'NF{print}' "${CHAPTERS_FILE}")
cd "${ROOT_DIR}"

# 优先使用 tectonic 的 PDF 引擎（若可用）
PDF_ENGINE="xelatex"
if command -v tectonic >/dev/null 2>&1; then
  PDF_ENGINE="tectonic"
fi

pandoc \
  --from=markdown+yaml_metadata_block+table_captions+tex_math_dollars+tex_math_single_backslash \
  --to=pdf \
  --pdf-engine=${PDF_ENGINE} \
  --metadata-file="${META_FILE}" \
  ${CHS_ARGS} \
  -o "${OUT_PDF}"

echo "PDF generated at: ${OUT_PDF}"


