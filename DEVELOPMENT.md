# Development

This is where the build-from-source, local-testing, and roadmap notes live — not in
`README.md`, since Home Assistant shows that file verbatim to end users in the Add-on Store.

## Assets

`icon.png`/`logo.png` are the "newspaper" symbol from Google's
[Material Symbols](https://github.com/google/material-design-icons) (`symbols/web/newspaper`),
licensed [Apache License 2.0](https://github.com/google/material-design-icons/blob/master/LICENSE)
— same license as this repo — recolored onto a solid background, no other modifications.

## Running locally (no Docker)

```bash
uv sync
./preview.sh                    # generate all enabled newspapers into output/, no upload
./preview.sh --newspaper <id>   # just one, by its "id" in addon_config.json
./run.sh                        # generate AND upload to reMarkable
```

`config/` holds your own real configuration and is gitignored — see [`examples/`](examples/) for
sanitized templates to copy in and adjust.

First upload needs reMarkable pairing: `uv run remarkapy init` (interactive, asks for the
8-character one-time code from https://my.remarkable.com/pair/app). The token lands in
`~/.rmapi` (or wherever `remarkapy`'s own config resolution finds/creates it) and is reused after
that.

## Running in Docker

The container runs `scheduler.py`, which reads every enabled newspaper's `schedule` cron string
from `addon_config.json` at startup and generates+uploads each one on its own cadence
(APScheduler, blocking process — this *is* the container's main process, no separate cron daemon).

```bash
./docker-build.sh
```

`/config` (read-only) holds `addon_config.json` + the referenced `*.goosepaper.json` files —
mounted from this repo's own `config/` directory by default. `/data` holds generated PDFs and the
reMarkable auth token (`HOME=/data` in the image, so `remarkapy` writes its token to
`/data/.rmapi`) — keep this volume around so pairing survives container recreation.

```bash
# one-time reMarkable pairing, against the same /data volume the scheduler will use later
mkdir -p data
docker run --rm -it -v "$(pwd)/data:/data" --entrypoint remarkapy goosepaper-addon init

./docker-run.sh             # starts the scheduler, foreground
```

The `goosepaper` dependency resolves via git from
[Smengerl/goosepaper-logicpuzzles](https://github.com/Smengerl/goosepaper-logicpuzzles) (`mainline`
branch), pinned to a specific commit in `uv.lock`; the image build uses `uv sync --frozen`, so it
always builds against exactly that commit, not whatever `mainline` has moved to since. To pick up
fork changes, run `uv lock` locally and commit the updated `uv.lock` (see `AGENTS.md`'s
"Dependency on the fork" section for the full procedure).

## Deploying to a real Home Assistant instance

See `AGENTS.md`'s "Deploying a change to the real add-on" section for the full checklist
(version bumps, Supervisor's store-cache behavior, expected build times on constrained hardware).

## Roadmap (post-v1 — deliberately deferred, not blocking an initial release)

- **Multi-arch + prebuilt image**: currently ships as a Supervisor build, `aarch64`-only —
  `config.yaml` has no `image:` field, so HA Supervisor builds the image on-device from this
  repo's `Dockerfile` on install. Verified working end-to-end on a real HA Green, but the build
  takes several minutes on that hardware, and there's no way for an amd64/armv7 user to install
  this at all today. **TODO**: add a GitHub Actions workflow (using the official
  [`home-assistant/builder`](https://github.com/home-assistant/builder) action) to build and push
  multi-arch images (at least `aarch64` + `amd64`) to a registry (e.g. `ghcr.io`) on each
  major/minor version bump, then add the matching `image:` field to `config.yaml`, so Supervisor
  pulls a prebuilt image instead of compiling WeasyPrint/Pango from source on every
  install/update. Deliberately bundled as one item and pushed past v1: it's a real chunk of
  CI/build-pipeline work on its own, and the on-device build - while slow - works correctly today
  for the one architecture the maintainer actually runs.
