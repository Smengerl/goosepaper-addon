# Goosepaper

Generates a personalized newspaper PDF and delivers it to your reMarkable tablet, on whatever
schedule you set — a fresh edition waiting for you every morning, no phone required.

Pull in what you actually want to read:

- **RSS feeds**, with built-in cleanup — strip ads, cookie banners, and paywall stubs out of
  articles, skip sponsored posts entirely, or narrow a general feed down to just the topics you
  care about (e.g. a single-company news ticker).
- **Wikipedia**'s current events.
- **Weather** forecasts for any location.
- **Puzzles** — Sudoku, Binoxxo, Futoshiki, Kakuro, and Shikaku, generated fresh each time, with
  optional solutions and rules explanations.
- **Daily comic strips** — XKCD, Calvin and Hobbes, or Garfield.

Run more than one newspaper at once — a daily news digest, a puzzle booklet for the weekend, a
kids' edition — each with its own schedule, sections, and reMarkable folder.

On first install, the add-on seeds itself with working example newspapers, ready to edit into
your own — you'll just need to pair a reMarkable before the add-on will start.

## Installation

[![Open your Home Assistant instance and show the add-on store with this repository pre-filled.](https://my.home-assistant.io/badges/supervisor_store.svg)](https://my.home-assistant.io/redirect/supervisor_store/?repository_url=https%3A%2F%2Fgithub.com%2FSmengerl%2Fgoosepaper-addon)

Or manually: **Settings → Add-ons → Add-on Store → ⋮ → Repositories**, add
`https://github.com/Smengerl/goosepaper-addon`, then install **Goosepaper** from the store.

See [DOCS.md](DOCS.md) for pairing your reMarkable and configuring newspapers after install.

**Full documentation** — configuration format, installation, and day-to-day usage — is in
[DOCS.md](DOCS.md), shown under this add-on's own Documentation tab in Home Assistant. Built on
[goosepaper-logicpuzzles](https://github.com/Smengerl/goosepaper-logicpuzzles), a public fork of
[goosepaper](https://github.com/j6k4m8/goosepaper).

---

Looking to build or contribute? See [DEVELOPMENT.md](DEVELOPMENT.md) for running this locally,
building the Docker image, and the project roadmap.
