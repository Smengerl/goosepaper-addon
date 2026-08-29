# Changelog

All notable changes to this add-on are documented here, grouped by the `config.yaml` version
they shipped in. Entries describe what changed for you as someone running the add-on - for the
full technical story behind any entry, follow its commit-history link.

## [1.9.2]

### Changed
- Comic sources (`"type": "comic"`) no longer show the strip's own name as a headline above
  the strip - it already draws its own title into the image, so the heading was a plain
  duplicate. The name is still shown wherever it was before *besides* directly above the
  strip: the table of contents (whether the source is grouped into a section or not) and, for
  the addon's own bundled `julian.goosepaper.json`, each of its 6 comics now gets its own named
  section (`"Garfield"`, `"Peanuts"`, `"Big Nate"`, `"FoxTrot"`, `"Wallace the Brave"`,
  `"Brewster Rockit"`) with the heading hidden via `section_heading_visible: false` (see
  1.9.1), instead of all 6 sharing one generic "Comics" section. `tagesgoose.goosepaper.json`'s
  XKCD source got the same treatment (its own `"XKCD"` section, heading hidden).

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/579e1a5...HEAD)

## [1.9.1]

### Added
- A `*.goosepaper.json` source can now set `"section_heading_visible": false` alongside
  `"section"` - keeps that group's entry in the table of contents while hiding the heading
  itself from the printed page. Useful for a section like a run of comic strips, where the
  strips already show their own titles inside the image and repeating the section name as
  running text would just be redundant.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/8b63c9c...579e1a5)

## [1.9.0]

### Added
- New **`locale`** add-on option (Settings → Add-ons → Goosepaper → Configuration) controls what
  language written-out month/weekday names render in when a newspaper's `datetime_format` uses
  `%B`/`%A` (e.g. `"%-d. %B %Y"` → "22. August 2026" with `locale` set to `de_DE`). Previously
  this always rendered in English regardless of the format string. Leave it empty (the default)
  to keep the previous English behavior - every installation may want a different language, so
  nothing is forced. See DOCS.md's "Language for date stamps" section.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/71954a4...8b63c9c)

## [1.8.0]

### Added
- A newspaper's `paper` settings can now set `datetime_format` to customize the generation-time
  stamp shown under the title, or set it to `null` to omit that stamp entirely - see
  [goosepaper-logicpuzzles#147](https://github.com/Smengerl/goosepaper-logicpuzzles/pull/147) for
  the accepted format. Existing newspapers are unaffected - the default matches the previous,
  always-on format.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/06d4ed3...71954a4)

## [1.7.8]

### Fixed
- An image that can't be loaded from its source page no longer produces a duplicate, confusing
  error in the log - just one clear line instead of two.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/15d6b34...06d4ed3)

## [1.7.7]

### Changed
- Generated PDFs are noticeably smaller - embedded images are now sized to fit the page/column
  they're actually shown at, instead of a fixed guess. No visible quality loss.

### Fixed
- Closed a security issue where a crafted image link on a comic source's page could inject
  unwanted markup into your generated PDF.
- Comic strips no longer occasionally lose their centering/caption styling.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/97b65bc...15d6b34)

## [1.7.6]

### Changed
- Puzzle rule text and the "Solution"/"How does X work?" headings are now in English instead of
  German. If your "Rätselheft" edition suddenly reads in English, that's this change - your own
  `section` labels (e.g. `"Sudoku Leicht"`) are unaffected.

### Fixed
- Kakuro clue numbers are now centered correctly in their triangles.
- The `prefer_feed_title` RSS option can now actually be used in a `.goosepaper.json` file
  (previously rejected with an error).

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/e5f937c...97b65bc)

## [1.7.5]

### Fixed
- RSS articles with short, heavily-formatted source HTML were sometimes wrongly kept or dropped
  by the article-length filter based on formatting, not actual content.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/3c36e49...e5f937c)

## [1.7.4]

### Added
- Comic sources: `comic_type` `"cah"`/`"garfield"` replaced by generic `"gocomics"`/`"arcamax"`
  plus a `comic_name` field, so any comic hosted on either site works, not just those two. If you
  use a `"comic"` source, update its config - see DOCS.md.

### Fixed
- RSS article images are now normalized before embedding, fixing a range of images (and
  sometimes whole stories) that could previously go missing from the PDF with no explanation.
- A comic strip not yet published for "today" now falls back to the previous day's instead of
  failing outright.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/ff6671c...3c36e49)

## [1.7.3]

### Fixed
- Some heise.de articles had their headline rendered twice in the PDF.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/3c0c0a3...ff6671c)

## [1.7.2]

### Fixed
- RSS images linked with a protocol-relative URL (`//host/path`) could silently go missing from
  the PDF.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/0b8b417...3c0c0a3)

## [1.7.1]

### Changed
- `addon_config.json`'s per-newspaper retention setting is simpler: `"retention": {"mode": ...,
  "keep_last_n": ...}` is now just `"retention_keep_last_n": N` (omit for no retention). Update
  your own `addon_config.json` if you use retention.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/c75d217...0b8b417)

## [1.7.0]

### Changed
- `*.goosepaper.json` newspaper files now use goosepaper's own native format directly instead of
  this add-on's translated one. **Existing newspaper files need migrating** - see DOCS.md for the
  new field names (`sections` → `sources` + `section` tag, `max_age_days` → `since_days_ago`,
  weather `units` → `unit`, and a required top-level `"version": 2`).

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/103889f...c75d217)

## [1.6.3]

### Changed
- Default max RSS article length raised (~1 page to ~2 pages per story).

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/2738684...103889f)

## [1.6.2]

### Removed
- The newspaper-wide `defaults` block for article-length limits - set `min_body_text_length`/
  `max_body_text_length` per `"rss"` source instead (same effect, simpler config). Existing
  shipped examples and configs already migrated.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/78153ea...2738684)

## [1.6.1]

### Fixed
- The `min_body_text_length`/`max_body_text_length`/`defaults` options are now actually
  documented in DOCS.md (previously only worked if you already knew they existed).

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/6481e96...78153ea)

## [1.6.0]

### Added
- A `*.goosepaper.json` file can now set a shared max RSS article length for the whole newspaper
  via a `defaults` block, instead of repeating it on every source.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/e0c7395...6481e96)

## [1.5.0]

### Fixed
- Emoji in RSS article text no longer render as empty boxes in the PDF.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/0ddb05a...e0c7395)

## [1.4.1]

Patch bump, no user-visible behavior change - ships packaging work (LICENSE/icon/logo) from 1.4.0
that Supervisor hadn't picked up yet.

### Removed
- The pairing code no longer auto-clears itself after use - it's still masked in the
  Configuration tab, and still single-use regardless, so this only affects whether the old value
  stays visible.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/c7006a6...0ddb05a)

## [1.4.0]

### Added
- A proper add-on icon/logo and an Installation section in the store listing.
- `generation_log_level` option to quiet down noisy generation logs (defaults to `warning`).
- The reMarkable pairing code field is now masked like a password.

### Fixed
- Pairing no longer crashes the add-on if a device token goes missing after startup.
- Delivery log messages ("Honk! Upload successful!") now show up immediately instead of being
  delayed, sometimes for hours.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/30fe250...c7006a6)

## [1.3.0]

### Added
- RSS sources can now cap maximum article length too (`max_body_text_length`), so one
  unusually long article can't balloon a whole edition.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/ab2f633...30fe250)

## [1.2.0]

### Changed
- The add-on now refuses to start if your reMarkable isn't properly paired, instead of starting
  anyway and only failing later when it tries to deliver.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/791d6ad...ab2f633)

## [1.1.0]

### Added
- Pair your reMarkable directly from the add-on's Configuration tab - no more shell/SSH access
  needed.
- New `"comic"` source type: embeds today's XKCD, Calvin and Hobbes, or Garfield strip.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/a44ee2c...791d6ad)

## [1.0.0]

Initial release: generates newspaper PDFs from RSS feeds, Wikipedia, weather, and puzzles,
delivered to a reMarkable tablet. Auto-seeds example newspapers on first install.

[Commits](https://github.com/Smengerl/goosepaper-addon/compare/dcc4695...a44ee2c)
