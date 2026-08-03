# Changelog

All notable changes to this add-on are documented here, grouped by the `config.yaml` version
they shipped in.

## [1.1.0]

### Added
- GUI-based reMarkable pairing: enter an 8-character pairing code directly under the add-on's
  Configuration tab (`remarkable_pairing_code`) instead of needing shell/SSH access.
- Startup pairing check: verifies (with a real API call, not just "does a token file exist")
  whether reMarkable pairing works every time the add-on starts. If there's no usable pairing at
  all, the add-on now refuses to start rather than silently scheduling newspapers that could only
  fail on delivery — a transient verification error against an already-paired token (e.g. a
  network hiccup at boot) does not block startup, only a genuinely missing/unusable pairing does.
- New `"comic"` source type: embeds today's XKCD, Calvin and Hobbes, or Garfield strip as an
  image story.
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
