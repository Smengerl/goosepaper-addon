#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

# /config: the addon config + *.goosepaper.json files, mounted read-only (edit them on the host).
# /data:   generated PDFs and the reMarkable auth token (~/.rmapi, since HOME=/data in the
#          image) - keep this across restarts so pairing only has to happen once. See README for
#          the one-time `remarkapy init` pairing step.
mkdir -p data

docker run --rm -it \
    -v "$(pwd)/config:/config:ro" \
    -v "$(pwd)/data:/data" \
    --name goosepaper-addon \
    goosepaper-addon "$@"
