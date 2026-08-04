# Changelog

All notable changes to this add-on are documented here, grouped by the `config.yaml` version
they shipped in.

## [1.4.0]

### Added
- `LICENSE` (Apache License 2.0) — matches the whole dependency chain (both
  `goosepaper-logicpuzzles` and `remarkapy` are already Apache-2.0), also added to
  `pyproject.toml`'s `license` field.
- `icon.png`/`logo.png` — the "newspaper" symbol from Google's Material Symbols (Apache-2.0),
  recolored; the add-on store previously showed a generic default icon. See DEVELOPMENT.md's
  "Assets" section for attribution.
- `CONTRIBUTING.md`, matching the maintainer's usual template across their other repos.
- README.md now states up front that this is a Home Assistant add-on, rather than only implying
  it later in the Installation section.
- Reworked the seeded example newspapers into three more realistic, distinct examples instead of
  a single generic "Daily News": **World News** (daily - BBC Politics/Business, CNBC, Garfield,
  Wikipedia, Berlin weather), **Tech Weekly** (weekly - The Verge/Ars Technica/TechCrunch/Wired/
  Engadget/The Register/Hacker News/InfoQ/GitHub Blog/Stack Overflow Blog/Dev.to, XKCD), and an
  expanded **Puzzle Booklet** (weekly - all 5 puzzle types at all 3 difficulties, 15 sections, up
  from 5). Verified end-to-end locally (`deliver.py`, no `--deliver`) - all three render cleanly.
- `hassio_api: true`: once a configured `remarkable_pairing_code` is successfully redeemed, the
  add-on now clears it back to empty via Supervisor's own API — a pairing code is single-use, so
  leaving the old one sitting in Configuration afterward looked reusable when it wasn't.
- `generation_log_level` option: sets the minimum log level for everything involved in actually
  generating an edition (WeasyPrint/font rendering, httpx's per-request logging, the scheduler
  library) — defaults to `warning`, since that output was burying this add-on's own `Honk!`
  messages under dozens of unrelated lines per edition. Those messages always show regardless of
  this setting, since they're on their own logger, pinned to `info` independent of the option.
- The startup "Configured newspapers" log now also shows each newspaper's resolved
  `*.goosepaper.json` path, and a note clarifying that file is reloaded fresh on every scheduled
  run (no restart needed to edit it) while `addon_config.json` itself needs a restart to pick up
  schedule/id/enabled changes.
- `_run_newspaper` now logs a "Finished scheduled generation" line on completion, not just on
  trigger/failure — a clear per-run end marker now that the underlying generation libraries'
  own completion chatter is filtered out by default.
- README.md now has an actual Installation section: a "My Home Assistant" one-click badge that
  opens the add-on store with this repository pre-filled, plus the manual
  Settings → Add-ons → Add-on Store → Repositories steps as a fallback.

### Changed
- `remarkable_pairing_code`'s schema type is now `password` instead of `str`, so the Configuration
  tab masks it like any other secret instead of leaving a one-time code sitting there in plain
  text after it's been entered and saved.

### Fixed
- `goosepaper.auth.auth_client()` (used for every reMarkable upload and retention cleanup, not
  just the startup pairing check) built its `Client` with remarkapy's `interactive=True` default —
  if a device token went missing after startup, that fell into an interactive `input()` pairing
  wizard, which just raised an uncaught `EOFError` in this container (no stdin) instead of the
  clean "Honk! Authentication failed" every caller already handles. Seen in production logs on an
  add-on that had never completed pairing. Now patched to `interactive=False` everywhere, matching
  what the startup check already guaranteed.
- `PYTHONUNBUFFERED=1`: the `goosepaper` dependency's own delivery messages ("Honk! Upload
  successful!" etc.) use `print()`, not `logging` - `logging`'s `StreamHandler` flushes after
  every record, but plain `print()`s stdout is block-buffered (not line-buffered) once it's piped
  rather than a TTY, which is always true under Docker. Without this, those messages could sit in
  the buffer for hours and only surface at the next restart - looking like they'd just happened
  when they were actually from a run hours earlier. Verified empirically: redirected stdout stays
  empty ~150ms after a `print()` without this set, appears immediately with it.
- `watchdog: true` (briefly added, now removed) turned out to use the wrong type - Supervisor's
  actual schema wants a URL/port template (`"tcp://[HOST]:[PORT]"` etc.) to actively health-check,
  not a boolean "restart on exit" toggle. Broke `config.yaml` parsing entirely - confirmed via
  Supervisor's own logs (`Can't read .../config.yaml: expected string or buffer for dictionary
  value @ data['watchdog']. Got True`) - which made every add-on in this repository disappear
  from the store (not just show stale) for as long as it was live. Removed outright rather than
  given a real target: this add-on has no listening port (headless scheduler, no `network`/
  `ingress`/`webui`), so there's nothing valid to health-check in the first place - saving a
  pairing code while the add-on is stopped needs a manual restart again, same as before 1.2.0.

## [1.3.0]

### Added
- `max_body_text_length` on `"rss"` sources (mirrors the existing `min_body_text_length`): drop
  stories whose extracted body is implausibly long — e.g. a hardware review with a huge photo
  gallery — instead of letting a single outlier balloon a whole edition.

### Changed
- `deliver.py`'s monkeypatches (RSS encoding fallback, per-entry RSS error handling, preferring
  the feed's own title over readability's, cross-source deduplication, and clean PDF bookmark
  levels) are gone — the same behavior is now native in the `goosepaper-logicpuzzles` fork
  itself, upstreamed from this add-on's own wrapper code. No behavior change; only the
  minimum/maximum-body-length safety net and section grouping remain wrapper-level concerns,
  since both depend on this add-on's own config schema.

## [1.2.0]

### Changed
- Startup pairing check now **refuses to start** if there's no usable reMarkable pairing at all
  (no token, and no working `remarkable_pairing_code` either), instead of only warning and then
  scheduling newspapers that could only fail on delivery — previously it logged a warning but
  still set up cron jobs and kept running. A transient verification error against an
  already-paired token (e.g. a network hiccup at boot) still does not block startup, only a
  genuinely missing/unusable pairing does.

### Added
- `translations/en.yaml` + `de.yaml`: the Configuration tab's `remarkable_pairing_code` field now
  has a friendly name and explanatory text (what it's for, where to get a code, and that it's
  only needed once or again after switching reMarkables) instead of just the bare option key.
- Startup "Configured newspapers" log summary: one line per newspaper (id, title, enabled state,
  cron schedule, reMarkable folder, retention policy, most recent local PDF) under the Log tab —
  a read-only overview of `addon_config.json` without needing a file editor. DOCS.md's new
  "Editing your configuration" section covers how to actually reach/edit the config files
  (Studio Code Server or Samba — there's no in-app editor on the Configuration tab).

### Fixed
- `config.yaml`'s `map:` used the deprecated `addon_config:rw`; switched to `app_config:rw`,
  matching Supervisor's in-progress "add-on → app" rename (the old value still works today but
  logs a "legacy map type" warning on every load).

## [1.1.0]

### Added
- GUI-based reMarkable pairing: enter an 8-character pairing code directly under the add-on's
  Configuration tab (`remarkable_pairing_code`) instead of needing shell/SSH access.
- Startup pairing check: verifies (with a real API call, not just "does a token file exist")
  whether reMarkable pairing works every time the add-on starts, and logs a clear warning if it's
  missing or invalid — newspaper generation still worked without it at this point, only
  reMarkable delivery needed it (tightened to a hard startup failure in 1.2.0).
- New `"comic"` source type: embeds today's XKCD, Calvin and Hobbes, or Garfield strip as an
  image story.

## [1.0.0]

Initial release.

### Added
- Home Assistant add-on packaging: `config.yaml`, `repository.yaml`, and the Dockerfile labels
  (`io.hass.version`/`io.hass.type`/`io.hass.arch`) Supervisor requires.
- Auto-seed: a fresh install with an empty `/config` is seeded with sanitized example newspapers
  on first start, so it produces a working PDF before any manual configuration.
- SIGTERM handling for clean shutdown; migrated logging from `print()` to Python's `logging`
  module throughout.
- Friendly startup errors for a malformed `addon_config.json` (a clear one-line log message)
  instead of a raw traceback.
- `content_accept_filters`/`accept_title_patterns` on `"rss"` sources — the allowlist
  counterparts to the existing `content_skip_filters`/`skip_title_patterns` — wired through from
  the fork.

### Fixed
- The Dockerfile depended on `libgdk-pixbuf-xlib-2.0-0`, a deprecated package that only worked
  because it transitively pulls in the real library WeasyPrint needs; switched to depending on
  `libgdk-pixbuf-2.0-0` directly.
- `.dockerignore` now excludes `config/` and `data/`, so real personal config or a paired
  reMarkable token can never end up baked into an image layer.
