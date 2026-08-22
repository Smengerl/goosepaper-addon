# Goosepaper — Documentation

A Home Assistant add-on wrapping
[goosepaper-logicpuzzles](https://github.com/Smengerl/goosepaper-logicpuzzles) (a public fork of
[goosepaper](https://github.com/j6k4m8/goosepaper)) — delivers a personalized newspaper PDF to a
reMarkable tablet, on a schedule you set per newspaper. This document covers what's specific to
running it as an add-on: installation, pairing, scheduling multiple newspapers, and retention.
For everything about what actually goes *into* an edition — available source types (RSS,
Wikipedia, weather, puzzles, comics, ...), filtering options, paper styling — see
[the fork's own README](https://github.com/Smengerl/goosepaper-logicpuzzles#readme); that's the
authoritative, up-to-date reference, not duplicated here.

## What it can do

**Multiple newspapers, independently scheduled.** Run a daily news digest, a weekend puzzle
booklet, or a kids' edition side by side — each with its own cron schedule, reMarkable folder,
and retention policy, defined once in `addon_config.json`.

**Automatic reMarkable delivery and retention.** Each edition uploads straight to a folder on
your reMarkable; `retention_keep_last_n` cleans up older editions there afterward so your device
doesn't accumulate every edition forever (see "Retention" below).

**Zero-effort first run.** A fresh install seeds itself with realistic example newspapers (see
"Installation" below), ready to go as soon as you've paired a reMarkable — no need to write a
config from scratch.

## Configuration: two layers

Both files live under `/config` — this add-on's own persistent, editable folder (see
Installation below for how to reach it). On first start, if `/config` is empty, the add-on
automatically seeds it with the sanitized examples from [`examples/`](examples/) — so you get a
working edition right away, with realistic content to edit rather than starting from a blank
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
      "retention_keep_last_n": 7
    }
  ]
}
```

`goosepaper_config` is resolved relative to `addon_config.json`'s own directory, so newspaper
files normally sit next to it under `/config`.

**`<name>.goosepaper.json`** (one per newspaper) is a plain goosepaper config — paper style plus a
list of sources — parsed entirely by goosepaper itself, not by this add-on. This add-on no longer
carries its own copy of that schema, so field names, available source types, and validation
errors all come straight from goosepaper; **[its README](https://github.com/Smengerl/goosepaper-logicpuzzles#readme)
is the authoritative, full reference** for everything a source can do (RSS filtering, puzzle/comic
options, weather, styling, ...) - not repeated here, so it can't drift out of sync with it.

The one thing worth knowing at the add-on level: any source can carry an optional `"section"` tag
to group it with others under a shared heading - handy once a newspaper mixes several sources:

```json
{
  "version": 2,
  "paper": { "style": "FifthAvenue", "font_size": 9 },
  "sources": [
    { "type": "rss", "url": "https://www.heise.de/rss/heise-atom.xml", "section": "Tech" }
  ]
}
```

See the shipped [`examples/`](examples/) for realistic, fuller configs (RSS filtering, puzzles,
comics, weather) to copy from and adapt.

## Installation

1. Add `https://github.com/Smengerl/goosepaper-addon` under **Settings → Add-ons → Add-on
   Store → ⋮ → Repositories**.
2. Install and start **Goosepaper** from the store. On first start it seeds `/config` with the
   example newspapers automatically (see Configuration above) — no manual setup needed to get a
   working config. It won't generate or schedule anything yet, though: pairing (next step) comes
   first. `/config` is the add-on's own private, persistent config storage — from any other
   add-on that mounts it, it shows up as `/addon_configs/626e47fd_goosepaper`
   ([Supervisor's documented convention](https://developers.home-assistant.io/docs/apps/configuration)
   for the `all_addon_configs`/`all_app_configs` map option; Supervisor is mid-rename from
   "add-on" to "app" terminology, so which of those two map *keywords* a given companion add-on
   declares varies — Samba and File editor already use `all_app_configs`, Terminal & SSH and
   Advanced SSH & Web Terminal still use `all_addon_configs` — but the mounted folder itself is
   `/addon_configs/...` either way). Reach it to edit those files with another add-on that can
   browse it (e.g. Samba, Studio Code Server, Terminal & SSH) — see "Editing your configuration"
   below for the concrete paths and gotchas for each.

   The `626e47fd_` prefix isn't installation-specific — Supervisor derives every add-on
   repository's store slug as the first 8 hex characters of `sha1(repository_url.lower())`. For
   the exact URL used in step 1 above, that hash is always `626e47fd`, so this folder name is the
   same for every user who added the repository with that URL. (Adding it with a trailing slash
   or a `.git` suffix would hash differently — stick to the URL as given.)
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

Two kinds of file matter day to day, both under `/config` (`/addon_configs/626e47fd_goosepaper`
from any other add-on that mounts it — see Installation above): `addon_config.json` (which
newspapers exist, their schedule, reMarkable folder, retention) and each newspaper's own
`*.goosepaper.json` (its sections, sources, paper look). There's no in-app editor for these on
the Configuration tab — Supervisor's Options UI only renders the schema fields under `options:`
in `config.yaml` (currently `remarkable_pairing_code` and `generation_log_level`), nothing
file-based. Reach the files instead with another add-on:

- **Studio Code Server** (Community add-on) — mounts every add-on's config folder automatically,
  no setup needed. Once installed, `goosepaper`'s files just show up in its file tree alongside
  your other add-ons'. Runs inside the HA web UI, so it's reachable from any browser but not as a
  regular filesystem mount on your own machine.
- **File editor** (Core add-on) — also mounts every add-on's config folder, but its
  **"Enforce Basepath"** option defaults to `true`, which restricts the file tree to `/config`
  only — so `goosepaper`'s folder won't show up until you turn that off under
  **Settings → Add-ons → File editor → Configuration** and restart the add-on. With it off,
  browse to `/addon_configs/626e47fd_goosepaper`.
- **Terminal & SSH** or **Advanced SSH & Web Terminal** (either add-on, if installed) — fastest
  way to just look, from a shell (Web Terminal or SSH client):
  ```bash
  ls -la /addon_configs/626e47fd_goosepaper/
  cat /addon_configs/626e47fd_goosepaper/addon_config.json
  ```
- **Samba share** (Community add-on) — the option to use when editing from an external/remote
  computer with your own editor rather than through the HA web UI. It exposes a network share
  named `addon_configs`; this add-on's files sit in the `626e47fd_goosepaper` folder inside it.
  Mount it as:
  - Windows: `\\<ha-host>\addon_configs\626e47fd_goosepaper`
  - macOS/Linux: `smb://<ha-host>/addon_configs/626e47fd_goosepaper`

  replacing `<ha-host>` with your Home Assistant's IP or hostname. (If your Supervisor version
  has renamed the share to `app_configs`, use that instead — check what your Samba add-on
  actually lists.)

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

`retention_keep_last_n` deletes older editions from the reMarkable folder after a successful
upload, keeping only the newest N. Omit it (or leave it unset) to never delete anything there.
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
