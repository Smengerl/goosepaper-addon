# Goosepaper

Generates personalized newspaper PDFs from RSS feeds (plus Wikipedia, weather, and puzzle
sections) and delivers them to a reMarkable tablet, on a schedule. Built on
[goosepaper-logicpuzzles](https://github.com/Smengerl/goosepaper-logicpuzzles), a public fork of
[goosepaper](https://github.com/j6k4m8/goosepaper) extended with a puzzle-generator provider
(Sudoku, Binoxxo, Futoshiki, Kakuro, Shikaku) and native RSS ad/paywall filtering.

Runs as a Home Assistant add-on (see `config.yaml`/`repository.yaml`) or standalone via Docker.
For configuration format, installation, and operation, see [DOCS.md](DOCS.md).

## Running locally (no Docker, for development)

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
that. On the actual add-on (via Docker/HA) this can also be done from the add-on's Configuration
GUI instead of a shell — see DOCS.md.

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
fork changes, run `uv lock` locally and commit the updated `uv.lock`.

> **Not yet tested end-to-end**: this development environment has no `docker` binary, so the
> `docker build`/`docker run` flow above, and the actual Home Assistant add-on install, are
> untested here. Local (`./preview.sh` / `./run.sh`) generation and upload, and the scheduler's
> job-registration and shutdown logic (`uv run python scheduler.py` against
> `config/addon_config.json`), are both verified.

Configuration format, retention, and HA installation are documented in [DOCS.md](DOCS.md).

## Roadmap

- **Build strategy**: currently ships as a Supervisor build — `config.yaml` has no `image:`
  field, so HA Supervisor builds the image on-device from this repo's `Dockerfile` on install.
  **TODO**: once the Supervisor-build path is confirmed working end-to-end, add a GitHub Actions
  workflow (using the official
  [`home-assistant/builder`](https://github.com/home-assistant/builder) action) to build and push
  multi-arch images to a registry (e.g. `ghcr.io`) on each version bump, then add the matching
  `image:` field to `config.yaml`. Saves users from building WeasyPrint/Pango/`uv sync` from
  source on constrained hardware (e.g. HA Green); not needed for a single-user Supervisor-build
  install.
