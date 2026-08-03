# Goosepaper — Documentation

Generates personalized newspaper PDFs from RSS feeds (plus Wikipedia, weather, puzzle, and comic
sections) and delivers them to a reMarkable tablet, on a schedule you set per newspaper. Built on
[goosepaper-logicpuzzles](https://github.com/Smengerl/goosepaper-logicpuzzles), a public fork of
[goosepaper](https://github.com/j6k4m8/goosepaper) extended with a puzzle-generator provider
(Sudoku, Binoxxo, Futoshiki, Kakuro, Shikaku), a daily-comic provider, and native RSS ad/paywall
filtering.

## What it can do

- **Multiple newspapers, independently scheduled.** Run a daily news digest, a weekend puzzle
  booklet, and a kids' edition side by side — each with its own cron schedule, reMarkable folder,
  and retention policy, defined once in `addon_config.json`.
- **RSS with real cleanup, not just raw feed dumps.** Strip ad blocks, cookie banners, and
  paywall stubs out of fetched articles; drop sponsored/paywalled entries entirely by title
  before they're even fetched; or go the other way and narrow a general feed down to just the
  entries you actually want (e.g. a single-company stock ticker out of a general business feed).
  See "Filtering RSS content" below for the full set of options.
- **Wikipedia**'s current-events section, no configuration needed beyond adding the source.
- **Weather** forecasts (Open-Meteo) for any location, in summary/hourly/daily form.
- **Logic puzzles** — Sudoku, Binoxxo, Futoshiki, Kakuro, Shikaku — generated fresh on every run
  (not pulled from a bank of pre-made puzzles), with configurable difficulty, and optional
  solutions/rules explanations placed inline, in a footer, or collected in an appendix at the end
  of the newspaper.
- **Daily comic strips** — XKCD, Calvin and Hobbes, or Garfield — embedded as an image story.
- **Automatic reMarkable delivery and retention.** Each edition uploads straight to a folder on
  your reMarkable; `retention.mode: "keep_last_n"` cleans up older editions there afterward so
  your device doesn't accumulate every edition forever (see "Retention" below).
- **Zero-effort first run.** A fresh install seeds itself with realistic example newspapers (see
  "Installation" below), ready to go as soon as you've paired a reMarkable — no need to write a
  config from scratch.

## Configuration: two layers

Both files live under `/config` — this add-on's own persistent, editable folder (see
Installation below for how to reach it). On first start, if `/config` is empty, the add-on
automatically seeds it with the sanitized examples from [`examples/`](examples/) — so you get a
working edition right away, with realistic sections to edit rather than starting from a blank
file. Edit the seeded `*.goosepaper.json` files (feeds, coordinates) and `addon_config.json`
(reMarkable folder, schedule) to make them yours; the add-on never overwrites files that already
exist.

**`addon_config.json`** holds only what a goosepaper config can't express — one entry per
newspaper, with its schedule, reMarkable folder, retention policy, and a path to its content:

```json
{
  "newspapers": [
    {
      "id": "daily-news",
      "enabled": true,
      "title": "Daily News",
      "schedule": "0 6 * * *",
      "goosepaper_config": "daily-news.goosepaper.json",
      "remarkable_folder": "Daily News",
      "retention": { "mode": "keep_last_n", "keep_last_n": 7 }
    }
  ]
}
```

`goosepaper_config` is resolved relative to `addon_config.json`'s own directory, so newspaper
files normally sit next to it under `/config`.

**`<name>.goosepaper.json`** (one per newspaper) holds the actual content — paper style and
sections, each with its sources:

```json
{
  "paper": { "style": "FifthAvenue", "font_size": 9, "layout": "auto", "table_of_contents": true },
  "sections": [
    {
      "title": "Tech",
      "sources": [
        {
          "name": "heise online",
          "url": "https://www.heise.de/rss/heise-atom.xml",
          "limit": 5,
          "max_age_days": 1,
          "skip_title_patterns": ["^anzeige:", "^heise-angebot:"],
          "content_skip_filters": [{ "type": "css", "selector": "div.Gallery" }]
        }
      ]
    }
  ]
}
```

Source `"type"` defaults to `"rss"` when omitted. Other types: `"wikipedia"`, `"weather"`
(Open-Meteo, needs `lat`/`lon`), `"puzzle"` (`puzzle_type`: sudoku/binoxxo/futoshiki/
kakuro/shikaku, plus `difficulty`, `count`, `box_size` for sudoku), and `"comic"`
(`comic_type`: xkcd/cah/garfield - downloads today's strip and embeds it as an image story).

### Filtering RSS content

An `"rss"` source can clean up fetched article HTML with `"content_skip_filters"`, a list of
filter objects — each object's `"type"` decides its shape, and each only accepts the keys valid
for its own type (a `"css"` filter can't also carry `"pattern"`/`"flags"`, nor can a `"regex"`
filter carry `"selector"` — rejected at config-load time, not just ignored):
- `{"type": "css", "selector": "..."}` — `selector` required — removes every element matching
  the selector, e.g. ad blocks or cookie banners.
- `{"type": "regex", "pattern": "...", "flags": "i"}` — `pattern` required, `flags` optional
  (any of `i`/`s`/`m`/`x`) — strips matching text from the raw HTML.

Skip whole entries by title instead with `"skip_title_patterns"` — unlike `content_skip_filters`,
a flat list of regexes with no object wrapper, matched case-insensitively against the entry
title.

Both have an "accept" counterpart for the inverse case — narrowing down instead of cleaning up.
`"content_accept_filters"` is a list of `{"selector": "..."}` objects — no `"type"` field at all,
CSS only — tried in list order, keeping only the first matching element's contents instead of the
whole parsed tree (useful when the fork's article extraction misses and you know exactly which
container holds the real content; falls through unchanged if nothing matches). `"accept_title_patterns"`
is, like `skip_title_patterns`, a flat list of regexes — only entries matching at least one are
kept, e.g. `["amazon", "amzn"]` on an otherwise general business feed, to build a single-company
news ticker.

All four fields are applied natively by the fork's
[`RSSFeedStoryProvider`](https://github.com/Smengerl/goosepaper-logicpuzzles/blob/mainline/goosepaper/storyprovider/rss.py)
— this project's own schema (`config_schema.py`) only validates their shape before passing them
through untouched.

An `"rss"` source can also set `"min_body_text_length"` and/or `"max_body_text_length"` (both
optional integers, applied after the filters above) to drop stories whose extracted body's
visible text length falls outside that range. `"min_body_text_length"` catches a failed
extraction (a near-empty body) — falls back to `defaults.min_body_text_length` (see the example
config above) when not set per-source. `"max_body_text_length"` catches the opposite: an article
whose body is implausibly long (e.g. a hardware review with a huge photo gallery), which would
otherwise balloon a single entry into the bulk of the whole edition — no default, opt in per
source. Both native to the fork's `RSSFeedStoryProvider` as well.

## Installation

1. Add `https://github.com/Smengerl/goosepaper-addon` under **Settings → Add-ons → Add-on
   Store → ⋮ → Repositories**.
2. Install and start **Goosepaper** from the store. On first start it seeds `/config` with the
   example newspapers automatically (see Configuration above) — no manual setup needed to get a
   working config. It won't generate or schedule anything yet, though: pairing (next step) comes
   first. `/config` is the add-on's own private, persistent config storage (maps to
   `/app_configs/goosepaper` on the host — some Supervisor versions still call this
   `/addon_configs/goosepaper`) — reach it to edit those files with another add-on that can
   browse it (e.g. Samba, Studio Code Server).
3. One-time reMarkable pairing — two ways:
   - **GUI (recommended)**: get an 8-character code from
     https://my.remarkable.com/pair/app, then enter it under **Settings → Add-ons → Goosepaper →
     Configuration** as `remarkable_pairing_code` and save (the field is masked, like any other
     secret). The add-on picks it up on its next (re)start — no shell access needed. Once the
     code is successfully redeemed, the add-on clears it back to empty on its own (a pairing code
     is single-use, so there's nothing left to reuse it for) — don't be surprised to find the
     field blank again afterward.
   - **Shell**: open a shell in the running add-on (or `docker exec` if run standalone) and run
     `remarkapy init`, which asks for the same kind of code interactively.

   Either way the token is written under `/data` (the add-on's private storage) and reused after
   that — pairing survives restarts and updates. The add-on checks pairing on every start and
   refuses to start if it's missing or no longer valid (see Logs below), rather than schedule
   newspapers that could only fail on delivery. If it's currently stopped for exactly that reason,
   saving a working pairing code is enough on its own — Supervisor's watchdog retries starting it
   automatically, no manual restart needed. A manual (re)start only matters if the add-on is
   otherwise running fine and you're just changing the code (e.g. re-pairing to a new tablet).
4. Edit the seeded `*.goosepaper.json` files and `addon_config.json` to your own feeds,
   reMarkable folder, and schedule (see "Editing your configuration" below for how to actually
   reach these files). It runs a scheduler (APScheduler, one cron job per enabled newspaper from
   `addon_config.json`) as its main process — editing a `*.goosepaper.json` file takes effect on
   the newspaper's next scheduled run; changing `addon_config.json` itself (schedule, id,
   enabled) needs an add-on restart, since the job list is built once at startup.

## Editing your configuration

Two kinds of file matter day to day, both under `/config` (`/app_configs/goosepaper` on the
host — see Installation above): `addon_config.json` (which newspapers exist, their schedule,
reMarkable folder, retention) and each newspaper's own `*.goosepaper.json` (its sections,
sources, paper look). There's no in-app editor for these on the Configuration tab — Supervisor's
Options UI only renders the schema fields under `options:` in `config.yaml` (currently just
`remarkable_pairing_code`), nothing file-based. Reach the files instead with another add-on:

- **Studio Code Server** (Community add-on) — mounts every add-on's config folder automatically,
  no setup needed. Once installed, `goosepaper`'s files just show up in its file tree alongside
  your other add-ons'.
- **Samba share** (Community add-on) — mount the add-on config folders as a network share and
  edit with any text editor on your machine.

After editing: a `*.goosepaper.json` change takes effect on that newspaper's next scheduled run,
no restart needed; an `addon_config.json` change (schedule, id, enabled, adding/removing a
newspaper) needs an add-on restart (see step 4 above for why). To sanity-check what's currently
configured without opening either add-on, see "Configured newspapers" next.

## Configured newspapers

Every start, the add-on logs a one-line summary per newspaper — id, title, enabled/disabled,
cron schedule, reMarkable folder, retention policy, and the most recently generated local PDF (if
any) — visible under the **Protokoll**/Log tab:

```
Honk! Configured newspapers (3):
Honk!   - tagesgoose 'Tagesgoose' - enabled, cron '0 6 * * *', folder 'Tagesgoose', retention: keep last 7, last local edition: Tagesgoose 2026-08-03.pdf
Honk!   - julian 'Julians Zeitung' - enabled, cron '0 18 * * 0', folder 'Julians Zeitung', retention: keep last 4, last local edition: Julians Zeitung 2026-08-03.pdf
```

This is read-only and reflects `addon_config.json` only (not each newspaper's sections/sources)
— it's a snapshot from startup, not live, so re-check it after a restart if you just edited
`addon_config.json`.

## Retention

`retention.mode: "keep_last_n"` deletes older editions from the reMarkable folder after a
successful upload, keeping only the newest `keep_last_n`. `"keep_all"` never deletes anything.
The most recently generated PDF is also always kept locally under `/data/output`, independent of
retention settings, so it stays inspectable without needing reMarkable access.

## Logs

The add-on logs to stdout/stderr (visible under the add-on's **Log** tab in HA), one line per
generation start, per delivered edition, per retention deletion, and per skipped/failed RSS
entry — each prefixed `Honk!`.
