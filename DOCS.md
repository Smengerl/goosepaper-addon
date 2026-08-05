# Goosepaper — Documentation

Generates personalized newspaper PDFs from RSS feeds (plus Wikipedia, weather, puzzle, and comic
sections) and delivers them to a reMarkable tablet, on a schedule you set per newspaper. Built on
[goosepaper-logicpuzzles](https://github.com/Smengerl/goosepaper-logicpuzzles), a public fork of
[goosepaper](https://github.com/j6k4m8/goosepaper) extended with a puzzle-generator provider
(Sudoku, Binoxxo, Futoshiki, Kakuro, Shikaku), a daily-comic provider, and native RSS ad/paywall
filtering.

## What it can do

**Multiple newspapers, independently scheduled.** Run a daily news digest, a weekend puzzle
booklet, or a kids' edition side by side — each with its own cron schedule, reMarkable folder,
and retention policy, defined once in `addon_config.json`.

Supports all features of the upstream goosepaper-logicpuzzles fork, including:

- **RSS feeds** including stripping ad blocks, cookie banners, and paywall stubs out of fetched articles
- **Wikipedia**'s current-events section.
- **Weather** forecasts (Open-Meteo) for any location.
- **Logic puzzles** — Sudoku, Binoxxo, Futoshiki, Kakuro, Shikaku — generated fresh on every run
  (not pulled from a bank of pre-made puzzles), with configurable difficulty.
- **Daily comic strips** — XKCD, Calvin and Hobbes, or Garfield — embedded as an image story.

**Automatic reMarkable delivery and retention.** Each edition uploads straight to a folder on
your reMarkable; `retention.mode: "keep_last_n"` cleans up older editions there afterward so
your device doesn't accumulate every edition forever (see "Retention" below).

**Zero-effort first run.** A fresh install seeds itself with realistic example newspapers (see
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
      "id": "world-news",
      "enabled": true,
      "title": "World News",
      "schedule": "0 6 * * *",
      "goosepaper_config": "world-news.goosepaper.json",
      "remarkable_folder": "World News",
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
     <https://my.remarkable.com/pair/app>, then enter it under **Settings → Add-ons → Goosepaper →
     Configuration** as `remarkable_pairing_code` and save (the field is masked, like any other
     secret). The add-on picks it up on its next (re)start — no shell access needed. It doesn't
     clear the field on its own afterward, but the code is single-use regardless, so leaving the
     old value there is harmless — clear it yourself if you'd rather not see it.
   - **Shell**: open a shell in the running add-on (or `docker exec` if run standalone) and run
     `remarkapy init`, which asks for the same kind of code interactively.

   Either way the token is written under `/data` (the add-on's private storage) and reused after
   that — pairing survives restarts and updates. The add-on checks pairing on every start and
   refuses to start if it's missing or no longer valid (see Logs below), rather than schedule
   newspapers that could only fail on delivery. If it's currently stopped for exactly that reason,
   saving a working pairing code alone doesn't bring it back — start it manually afterward (a
   headless add-on like this one has no listening port for Supervisor's watchdog to health-check,
   so that can't restart it automatically).
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
Options UI only renders the schema fields under `options:` in `config.yaml` (currently
`remarkable_pairing_code` and `generation_log_level`), nothing file-based. Reach the files
instead with another add-on:

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
cron schedule, the resolved path to its `*.goosepaper.json`, reMarkable folder, retention policy,
and the most recently generated local PDF (if any) — visible under the **Protokoll**/Log tab:

```
Honk! Configured newspapers (3), read from /config/addon_config.json:
Honk!   - world-news 'World News' - enabled, cron '0 6 * * *', config /config/world-news.goosepaper.json, folder 'World News', retention: keep last 7, last local edition: World News 2026-08-03.pdf
Honk!   - tech-weekly 'Tech Weekly' - enabled, cron '0 7 * * 6', config /config/tech-weekly.goosepaper.json, folder 'Tech Weekly', retention: keep last 4, last local edition: none yet
Honk!   - puzzles 'Puzzle Booklet' - enabled, cron '0 8 * * 0', config /config/puzzle-booklet.goosepaper.json, folder 'Puzzle Booklet', retention: keep last 4, last local edition: none yet
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
entry — each prefixed `Honk!`. Messages with that prefix always show, regardless of the setting
below — they're this add-on's own, not the underlying generation libraries'.

A single edition also pulls in WeasyPrint (PDF/font rendering), httpx (every HTTP request), and
the scheduler library, all of which log their own step-by-step detail at `info` by default —
enough to bury the `Honk!` lines under dozens of unrelated ones per run. **`generation_log_level`**
(Settings → Add-ons → Goosepaper → Configuration) sets the minimum level for that underlying
noise; it defaults to `warning` to keep the log readable. Set it to `debug` or `info` temporarily
when you actually need that detail, e.g. tracking down why a specific RSS entry got skipped.
