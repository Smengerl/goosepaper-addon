# Changelog

All notable changes to this add-on are documented here, grouped by the `config.yaml` version
they shipped in.

## [1.6.2]

### Removed
- The `defaults` block introduced in 1.6.0/1.6.1 (`config_schema.py`'s `Defaults` model, its
  `min_body_text_length`/`max_body_text_length` merge in `deliver.py`'s `_build_provider`).
  Reconsidered after a closer look: this was an addon-only abstraction with no equivalent in
  goosepaper's own native config schema (which has no "defaults" concept at all - every source is
  always specified individually there). A per-source-type defaults mechanism is arguably useful
  in general (`byline`/`body_source` are just as repetitive across sources as the two length
  fields were), but if it's worth having, it belongs in goosepaper itself where every user
  benefits - not duplicated here as addon-only scope creep. `RSSSource.min_body_text_length`/
  `max_body_text_length` are unaffected (still per-source, optional, unchanged) - only the
  newspaper-wide fallback is gone.
- `min_body_text_length: 120`/`max_body_text_length: 4000` are now set explicitly on every `"rss"`
  source in both shipped examples and the maintainer's own live newspapers, instead of once via
  `defaults` - same effective values as 1.6.0/1.6.1, just spelled out per source rather than
  inherited. `raetselheft` and `puzzle-booklet` had the now-removed `defaults` key dropped too
  (neither has any `"rss"` sources for it to have applied to).

## [1.6.1]

### Fixed
- `min_body_text_length`/`max_body_text_length` and the `defaults` block were entirely
  undocumented - zero mentions across README.md/DOCS.md/DEVELOPMENT.md/CONTRIBUTING.md, and no
  explanatory comments on `RSSSource`'s two fields or the `Defaults` model itself (unlike every
  other field in `config_schema.py`). Found while double-checking whether the `defaults`
  mechanism needed to go into the upstream PR for the per-source fields (it doesn't - `defaults`
  is a pure addon-side wrapper concept, goosepaper's own native schema has no such thing). Added
  to DOCS.md's "Configuration: two layers" example, plus docstrings on both spots in
  `config_schema.py`: the `defaults` block applies per newspaper file, not addon-wide; a source's
  own value always overrides it; `min_body_text_length` defaults to `120` even if `defaults` is
  omitted entirely, `max_body_text_length` has no built-in default.

## [1.6.0]

### Added
- `defaults.max_body_text_length` in a `*.goosepaper.json` file's top-level `defaults` block -
  mirrors the existing `defaults.min_body_text_length`, applying a shared cap to every `"rss"`
  source that doesn't set its own `max_body_text_length` (a per-source override already existed
  on `RSSSource`, but `Defaults` and `deliver.py`'s merge logic only ever knew about the minimum
  side - `config_schema.py`'s `Defaults` model didn't have the field at all, so it wasn't even
  possible to set this via `defaults`, only per source).
- Set to `4000` in both shipped examples (`world-news`, `tech-weekly`) and both of the
  maintainer's own live newspapers with RSS sources (`tagesgoose`, `julian` - `raetselheft` has
  none). Chosen empirically, not guessed: rendered a single placeholder story through the real
  pipeline (`page_profile: paper_pro`, `font_size: 9`, 2-column layout) for both `FifthAvenue` and
  `Autumn` (the two styles actually in use) and binary-searched for where it just spills onto a
  second page - landed at ~4000-4100 visible characters for both styles, so one shared value
  works across both. Verified against real, currently-live feeds (not synthetic text): with the
  limit off, 31 of 115 fetched `tagesgoose` stories exceeded 4000 characters (up to 38,400 from a
  single InfoQ conference-talk writeup); with it on, the longest surviving story was 3,997.

## [1.5.0]

### Added
- `fonts-noto-color-emoji` in the Dockerfile: `fonts-dejavu-core`/`fonts-liberation` (the only
  fonts previously installed) have no emoji glyphs, so any emoji in RSS-sourced article text
  rendered as an empty tofu box in the PDF - confirmed in production logs from the 1.4 run. This
  only affects this add-on's own Docker image, not `goosepaper-logicpuzzles` or regular
  goosepaper usage generally, so it's fixed here rather than upstreamed.
  - Corrects an earlier assumption made while scoping this fix: there is no monochrome
    `fonts-noto-emoji` Debian package - `fonts-noto-color-emoji` is the only Noto emoji font
    Debian actually packages, confirmed by searching the archive directly rather than guessing
    from the upstream GitHub repo's file layout.
  - Verified locally before shipping: downloaded the exact `.deb` Debian bookworm ships
    (`fonts-noto-color-emoji_2.042-0+deb12u1_all.deb`, matching this image's base), extracted the
    real font file, and rendered a test PDF with WeasyPrint 68.1 (the pinned version) using an
    isolated fontconfig setup that only exposes the same three font packages this Dockerfile
    installs - macOS's own emoji font was excluded so the test couldn't accidentally pass for the
    wrong reason. First attempt rendered emoji at wildly oversized, layout-breaking dimensions -
    traced to a missing `10-scale-bitmap-fonts.conf` fontconfig rule (a known fix for
    CBDT/CBLC-format color bitmap fonts, standard in fontconfig >=2.13.1). Confirmed
    `libpangoft2-1.0-0` (already in this Dockerfile) depends on `libfontconfig1` ->
    `fontconfig-config`, which ships that rule by default - so no extra Dockerfile line is needed
    for it, and the real container isn't expected to hit the oversized-glyph problem seen in the
    deliberately minimal test config. Re-tested with the rule included: emoji render correctly
    sized, inline with body text. See DEVELOPMENT.md's "Assets" section for the font's actual
    license (SIL OFL 1.1, verified from Debian's own package metadata).
  - Trade-off: each emoji is now an embedded color bitmap rather than absent, so generated PDFs
    with emoji-heavy content will be somewhat larger; the font itself adds ~11 MB to the image.
  - Known limitation: some multi-codepoint ZWJ sequences (e.g. the four-person family emoji) render
    as separate component glyphs side by side rather than one combined glyph - a limitation of this
    font build, not of the fix. Simple emoji, flags, and skin-tone modifiers all render correctly.

## [1.4.1]

Version-only bump, no functional changes - forces Supervisor to notice the LICENSE/icon/logo/
CONTRIBUTING.md work below, which shipped without a version change and so wasn't detected as an
update (see AGENTS.md's "Versioning and git tags" - this is exactly the patch-bump case it
describes: no new git tag for this one, `v1.4.0` stays the reference point).

### Removed
- `hassio_api: true` and the pairing-code self-clear it enabled (1.4.0's "Added" entry above) -
  rolled back after an aggressive-complexity review. The actual problem (a one-time code sitting
  visibly in Configuration) was already solved by masking the field as `password`; auto-clearing
  it on top was cosmetic-only polish bought with an elevated Supervisor permission, a runtime
  network dependency, and ~30 lines of code. `remarkable_pairing_code` no longer clears itself -
  it's still masked, and still single-use regardless, so an old value sitting there is harmless.

### Fixed
- `deliver.py` and `scheduler.py` each independently re-implemented the same "resolve
  `goosepaper_config` relative to `addon_config.json`'s directory" logic - now lives once, in
  `config_schema.resolve_goosepaper_config_path()`.
- `scheduler.py` had three separate call sites independently reading and error-handling
  `/data/options.json` - consolidated into one `_read_options()` helper.
- `config_schema.py`'s `schedule` field comment said "informational until this is containerized"
  - stale since the add-on *is* the container, and `CronTrigger.from_crontab()` reads this field
  for real.
- `CONTRIBUTING.md` pointed at `generic_filters.py` as a good place to add tests; that file no
  longer exists (removed when the fork absorbed its functionality natively) - now points at
  `config_schema.py` instead.
- `CONTRIBUTING.md`'s "Development Setup" duplicated `DEVELOPMENT.md`'s "Running locally"
  instructions nearly verbatim - now links to it instead of repeating the commands.
- `config_schema.py`'s module docstring pointed at `../goosepaper-fork/...` for the upstream RSS
  provider source - that directory has never existed under that name; the actual sibling checkout
  is `goosepaper-logicpuzzles`.
- `DOCS.md`'s "Configured newspapers" example log block still showed the maintainer's old
  personal newspaper names (`tagesgoose`, plus a mismatched `julian`/`Techweekly` leftover) rather
  than the actual shipped examples (`world-news`/`tech-weekly`/`puzzles`).
- `AGENTS.md` pointed at "the Roadmap section in `README.md`" - it lives in `DEVELOPMENT.md`;
  README.md has no Roadmap section at all.

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
