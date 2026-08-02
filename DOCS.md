# Goosepaper — Documentation

Generates personalized newspaper PDFs from RSS feeds (plus Wikipedia, weather, and puzzle
sections) and delivers them to a reMarkable tablet, on a schedule you set per newspaper. Built on
[goosepaper-logicpuzzles](https://github.com/Smengerl/goosepaper-logicpuzzles), a public fork of
[goosepaper](https://github.com/j6k4m8/goosepaper) extended with a puzzle-generator provider
(Sudoku, Binoxxo, Futoshiki, Kakuro, Shikaku) and native RSS ad/paywall filtering.

## Configuration: two layers

Both files live under `/config` — this add-on's own persistent, editable folder (see
Installation below for how to reach it). Sanitized starting points for both live in
[`examples/`](examples/) — copy them into `/config` and adjust feeds/coordinates/schedules to
your own.

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
(Open-Meteo, needs `lat`/`lon`), and `"puzzle"` (`puzzle_type`: sudoku/binoxxo/futoshiki/
kakuro/shikaku, plus `difficulty`, `count`, `box_size` for sudoku). `content_skip_filters`/
`skip_title_patterns` on an `"rss"` source are applied natively by the fork's
[`RSSFeedStoryProvider`](https://github.com/Smengerl/goosepaper-logicpuzzles/blob/mainline/goosepaper/storyprovider/rss.py).

## Installation

1. Add this repository under **Settings → Add-ons → Add-on Store → ⋮ → Repositories**. This repo
   is **private** (it contains real config files with personal data — feed lists, home
   coordinates, reMarkable folder names), so a plain `https://github.com/Smengerl/goosepaper-addon`
   URL will fail with a permission error. Use a URL with a
   [GitHub personal access token](https://github.com/settings/tokens) (repo-scoped, read-only is
   enough) embedded instead:
   `https://<token>@github.com/Smengerl/goosepaper-addon`. Do not make the repo public as a
   workaround — it would publish that personal data.
2. Install **Goosepaper** from the store.
3. Populate `/config` with an `addon_config.json` and its referenced `*.goosepaper.json` files.
   This folder is the add-on's own private, persistent config storage (maps to
   `/addon_configs/goosepaper` on the host) — reach it with another add-on that can browse
   `/addon_configs` (e.g. Samba, Studio Code Server), or by editing the files before first start
   and copying them in.
4. One-time reMarkable pairing: open a shell in the running add-on (or `docker exec` if run
   standalone) and run `remarkapy init`, which asks for the one-time code from
   https://my.remarkable.com/device/browser/connect. The token is written under `/data` (the
   add-on's private storage) and reused after that — pairing survives restarts and updates.
5. Start the add-on. It runs a scheduler (APScheduler, one cron job per enabled newspaper from
   `addon_config.json`) as its main process — editing a `*.goosepaper.json` file takes effect on
   the newspaper's next scheduled run; changing `addon_config.json` itself (schedule, id,
   enabled) needs an add-on restart, since the job list is built once at startup.

## Retention

`retention.mode: "keep_last_n"` deletes older editions from the reMarkable folder after a
successful upload, keeping only the newest `keep_last_n`. `"keep_all"` never deletes anything.
The most recently generated PDF is also always kept locally under `/data/output`, independent of
retention settings, so it stays inspectable without needing reMarkable access.

## Logs

The add-on logs to stdout/stderr (visible under the add-on's **Log** tab in HA), one line per
generation start, per delivered edition, per retention deletion, and per skipped/failed RSS
entry — each prefixed `Honk!`.
