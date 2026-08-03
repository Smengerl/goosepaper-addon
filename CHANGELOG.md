# Changelog

All notable changes to this add-on are documented here, grouped by the `config.yaml` version
they shipped in.

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
