#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib:${DYLD_FALLBACK_LIBRARY_PATH:-}"

mkdir -p output
uv sync --quiet
uv run python deliver.py --config config/addon_config.json --output output "$@"
echo "Preview(s) written to output/ (not uploaded)."
