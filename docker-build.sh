#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

# pyproject.toml's goosepaper dependency resolves via git from
# https://github.com/Smengerl/goosepaper-logicpuzzles, so a plain build is enough - no local
# checkout, no second build context.
docker build -t goosepaper-addon .
