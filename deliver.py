"""Multi-newspaper generator + reMarkable uploader, driven by a two-layer config
(config_schema.py): `addon_config.json` (schedule/folder/retention/which content file - what
will eventually be this add-on's own options) plus one `*.goosepaper.json` file per newspaper
(sections/sources/paper look - the actual content, editable without touching addon options).

Depends on ../goosepaper-fork (a local editable install, see pyproject.toml) instead of the
PyPI `goosepaper` package - that fork adds a native "puzzle" source type and native
`content_skip_filters`/`skip_title_patterns` support on `"rss"` sources (see its own deliver.py-free
goosepaper/storyprovider/rss.py and goosepaper/storyprovider/puzzle.py). Everything below is
generic, source-agnostic behavior that stays a wrapper concern rather than living in the fork -
see the plan history for why each item is scoped where it is:

1. remarkapy reads the account's sync `schemaVersion` from the root manifest and reuses it for
   writes. Accounts still on schema 3 get rejected by the cloud on every write ("Software must be
   updated" / update-required) even though the server accepts schema-4 writes just fine. Until
   upstream remarkapy handles this (https://github.com/j6k4m8/remarkapy), force schema 4.
2. goosepaper's RSS provider (body_source="article") fetches the full article page with
   `requests` and trusts `response.encoding`. Per RFC 2616, `requests` defaults undeclared text/*
   charsets to ISO-8859-1, mangling UTF-8 pages that omit an explicit charset. Fall back to
   requests' own content-sniffed encoding whenever the header didn't declare one.
3. readability's `doc.title()` is unreliable on some sites (e.g. it returns just the site name
   for every Golem article). The RSS feed's own <title> is always accurate; use it always.
4. `RSSFeedStoryProvider.get_stories()` has no per-entry error handling: one broken link (e.g.
   Hacker News linking out to a dead or SSL-broken third-party site) raises out of the whole
   method and drops that source's entire batch for the run. Catch and skip per entry instead.
5. Cross-source deduplication (goosepaper has a built-in `deduplicate` option on
   `Goosepaper.get_stories()` that matches identical headline+date, but the upstream CLI never
   enables it). Force it on.
6. WeasyPrint's PDF outline is built from every <h1>-<h6> by default, including headings that
   originate inside a story's own body content. bookmarks.css assigns explicit bookmark-level
   values (section=1, headline=2, in-body headings=none) for a clean two-level outline.

Per-newspaper/per-section/per-source behavior (sections grouping, the minimum-body-length safety
net) is config-driven via GoosepaperConfig/generic_filters.py, applied in ConfiguredRSSProvider
and SectionTaggedProvider below.
"""

from __future__ import annotations

import argparse
import datetime
import logging
import pathlib
import sys
from typing import List, Optional

import remarkapy.client as _rc_client

import config_schema
import generic_filters

logger = logging.getLogger("goosepaper-addon")

# --- generic, always-on monkeypatches ----------------------------------------------------------

_original_get_root_state = _rc_client.Client.get_root_state


def _patched_get_root_state(self, refresh=False):
    root_hash, generation, _schema_version = _original_get_root_state(self, refresh=refresh)
    self._root_state = (root_hash, generation, 4)
    return self._root_state


_rc_client.Client.get_root_state = _patched_get_root_state

import goosepaper.storyprovider.rss as _rss

_original_story_from_response = _rss._story_from_response
_original_story_from_entry = _rss._story_from_entry


def _patched_story_from_response(entry, response, source, date, fallback_body_html=""):
    content_type = response.headers.get("content-type", "")
    if "charset" not in content_type.lower():
        response.encoding = response.apparent_encoding or "utf-8"
    story = _original_story_from_response(entry, response, source, date, fallback_body_html)
    story.headline = entry["title"]
    return story


_rss._story_from_response = _patched_story_from_response


def _patched_story_from_entry(entry, source, date, body_source="auto"):
    try:
        return _original_story_from_entry(entry, source, date, body_source=body_source)
    except Exception as err:
        logger.warning("Honk! Skipping %r: %s", entry.get("link", entry.get("title")), err)
        return None


_rss._story_from_entry = _patched_story_from_entry

import goosepaper.goosepaper as _gp

_original_get_stories = _gp.Goosepaper.get_stories


def _patched_get_stories(self, deduplicate: bool = True):
    return _original_get_stories(self, deduplicate=deduplicate)


_gp.Goosepaper.get_stories = _patched_get_stories

import goosepaper.styles as _styles

_original_get_stylesheets = _styles.Style.get_stylesheets
_BOOKMARKS_CSS_PATH = str(pathlib.Path(__file__).resolve().parent / "bookmarks.css")


def _patched_get_stylesheets(self) -> List[str]:
    return [*_original_get_stylesheets(self), _BOOKMARKS_CSS_PATH]


_styles.Style.get_stylesheets = _patched_get_stylesheets

# Import after the monkeypatches above so every code path already sees the patched behavior.
from goosepaper.auth import auth_client  # noqa: E402
from goosepaper.goosepaper import Goosepaper  # noqa: E402
from goosepaper.storyprovider.puzzle import PuzzleStoryProvider  # noqa: E402
from goosepaper.storyprovider.rss import RSSFeedStoryProvider  # noqa: E402
from goosepaper.storyprovider.storyprovider import StoryProvider  # noqa: E402
from goosepaper.storyprovider.weather import OpenMeteoWeatherStoryProvider  # noqa: E402
from goosepaper.storyprovider.wikipedia import (  # noqa: E402
    WikipediaCurrentEventsStoryProvider,
)
from goosepaper.upload import upload as goosepaper_upload  # noqa: E402


# --- per-source, config-driven post-processing -------------------------------------------------


class ConfiguredRSSProvider(StoryProvider):
    """Wraps the fork's RSSFeedStoryProvider (which now natively applies content_skip_filters/
    skip_title_patterns) with what's still wrapper-only: section tagging and the minimum-body-
    length safety net."""

    def __init__(
        self,
        source: config_schema.RSSSource,
        section_title: str,
        default_min_body_text_length: int,
    ) -> None:
        self._min_len = source.min_body_text_length or default_min_body_text_length
        self._section_title = section_title
        self._inner = RSSFeedStoryProvider(
            rss_path=source.url,
            limit=source.limit,
            since_days_ago=source.max_age_days,
            byline=source.byline,
            body_source=source.body_source,
            content_skip_filters=[
                f.model_dump(exclude_none=True) for f in source.content_skip_filters
            ],
            skip_title_patterns=source.skip_title_patterns,
            content_accept_filters=[
                f.model_dump(exclude_none=True) for f in source.content_accept_filters
            ],
            accept_title_patterns=source.accept_title_patterns,
        )

    def get_stories(self) -> List:
        kept = []
        for story in self._inner.get_stories():
            if generic_filters.visible_text_length(story.body_html) < self._min_len:
                continue
            story.section_title = self._section_title
            kept.append(story)
        return kept


class SectionTaggedProvider(StoryProvider):
    """Tags every story from a built-in goosepaper provider (Wikipedia, weather, puzzle, ...)
    with its section - the only per-source-config concern that applies to non-RSS providers too,
    since they don't scrape arbitrary HTML and so have no clutter to filter or titles to skip.

    `headline_prefix`, if given, is prepended to every returned headline - used for weather,
    since OpenMeteoWeatherStoryProvider always returns the bare headline "Weather" with no place
    name (Open-Meteo's API has no reverse-geocoding), so there'd otherwise be no way to tell two
    weather sections apart.
    """

    def __init__(self, inner: StoryProvider, section_title: str, headline_prefix: str = "") -> None:
        self._inner = inner
        self._section_title = section_title
        self._headline_prefix = headline_prefix

    def get_stories(self) -> List:
        stories = self._inner.get_stories()
        for story in stories:
            story.section_title = self._section_title
            if self._headline_prefix:
                story.headline = f"{self._headline_prefix}: {story.headline}"
        return stories


def _build_provider(
    source: config_schema.Source, section_title: str, defaults: config_schema.Defaults
) -> StoryProvider:
    if source.type == "rss":
        return ConfiguredRSSProvider(source, section_title, defaults.min_body_text_length)
    if source.type == "wikipedia":
        return SectionTaggedProvider(WikipediaCurrentEventsStoryProvider(), section_title)
    if source.type == "weather":
        return SectionTaggedProvider(
            OpenMeteoWeatherStoryProvider(
                lat=source.lat,
                lon=source.lon,
                F=source.units == "fahrenheit",
                timezone=source.timezone,
                mode=source.mode,
                days=source.days,
                clock_format=source.clock_format,
            ),
            section_title,
            headline_prefix=source.name,
        )
    if source.type == "puzzle":
        kwargs = {"puzzle_type": source.puzzle_type, "difficulty": source.difficulty,
                  "count": source.count, "seed": source.seed, "explanation": source.explanation,
                  "name": source.name}
        if source.puzzle_type == "sudoku":
            kwargs["box_size"] = source.box_size
        return SectionTaggedProvider(PuzzleStoryProvider(**kwargs), section_title)
    raise ValueError(f"Unknown source type {source.type!r}")


def _build_providers(
    goosepaper_config: config_schema.GoosepaperConfig,
) -> List[StoryProvider]:
    providers = []
    for section in goosepaper_config.sections:
        for source in section.sources:
            providers.append(_build_provider(source, section.title, goosepaper_config.defaults))
    return providers


def _cleanup_old_editions(entry: config_schema.AddonNewspaperEntry) -> None:
    retention = entry.retention
    if retention.mode != "keep_last_n":
        return

    client = auth_client()
    if not client:
        logger.warning("Honk! Could not authenticate for retention cleanup, skipping.")
        return

    items = [item for item in client.list_items() if item.parent != "trash"]
    folder = next(
        (
            item
            for item in items
            if item.is_collection
            and item.visibleName == entry.remarkable_folder
            and item.parent == ""
        ),
        None,
    )
    if folder is None:
        return

    prefix = f"{entry.title} "
    editions = sorted(
        (
            item
            for item in items
            if item.type == "DocumentType"
            and item.parent == folder.id
            and item.visibleName.startswith(prefix)
        ),
        key=lambda item: item.visibleName,
        reverse=True,
    )
    for stale in editions[retention.keep_last_n :]:
        logger.info("Honk! Retention: deleting old edition %r", stale.visibleName)
        client.delete(stale.id, refresh=True)


def _cleanup_local_editions(
    entry: config_schema.AddonNewspaperEntry, output_path: pathlib.Path, out_dir: pathlib.Path
) -> None:
    """Keep only the just-generated edition of `entry` in `out_dir`, deleting older local PDFs
    for the same newspaper. Runs after a successful upload - goosepaper's own `cleanup` delivery
    setting is left off (see `run()`) precisely so the latest edition survives locally instead of
    being removed the moment it's uploaded; this is what actually enforces "only the latest"."""
    prefix = f"{entry.title} "
    for stale in out_dir.glob(f"{prefix}*.pdf"):
        if stale == output_path:
            continue
        logger.info("Honk! Local retention: deleting old local edition %r", stale.name)
        stale.unlink()


def _generate_newspaper(
    entry: config_schema.AddonNewspaperEntry,
    goosepaper_config: config_schema.GoosepaperConfig,
    output_dir: pathlib.Path,
) -> pathlib.Path:
    providers = _build_providers(goosepaper_config)
    paper = Goosepaper(story_providers=providers, title=entry.title)

    output_dir.mkdir(parents=True, exist_ok=True)
    edition_name = f"{entry.title} {datetime.date.today().isoformat()}"
    output_path = output_dir / f"{edition_name}.pdf"

    paper.to_pdf(
        str(output_path),
        font_size=goosepaper_config.paper.font_size,
        style=goosepaper_config.paper.style,
        table_of_contents=goosepaper_config.paper.table_of_contents,
        layout=goosepaper_config.paper.layout,
        page_profile=goosepaper_config.paper.page_profile,
    )
    return output_path


def run(addon_config_path: str, deliver: bool, newspaper_id: Optional[str], output_dir: str) -> int:
    try:
        addon_config = config_schema.load_addon_config(addon_config_path)
    except Exception as err:
        logger.error("Honk! Could not load %s: %s", addon_config_path, err)
        return 1
    base_dir = pathlib.Path(addon_config_path).resolve().parent

    newspapers = [n for n in addon_config.newspapers if n.enabled]
    if newspaper_id:
        newspapers = [n for n in newspapers if n.id == newspaper_id]
        if not newspapers:
            logger.error("Honk! No enabled newspaper with id %r found.", newspaper_id)
            return 1

    out_dir = pathlib.Path(output_dir)
    for entry in newspapers:
        config_path = pathlib.Path(entry.goosepaper_config)
        if not config_path.is_absolute():
            config_path = base_dir / config_path
        try:
            goosepaper_config = config_schema.load_goosepaper_config(config_path)
        except Exception as err:
            logger.error("Honk! Could not load %s for %r: %s", config_path, entry.title, err)
            continue

        logger.info("Honk! Generating %r (from %s)...", entry.title, config_path)
        output_path = _generate_newspaper(entry, goosepaper_config, out_dir)
        logger.info("Honk! Wrote %s", output_path)

        if not deliver:
            continue

        result = goosepaper_upload(
            filepath=str(output_path),
            delivery_settings={
                "folder": entry.remarkable_folder,
                "replace_mode": "nocase",
                # Left off deliberately: the local file is kept (see _cleanup_local_editions
                # below), not removed the instant it's uploaded, so the last generated edition
                # stays inspectable in output/ - e.g. via the HA add-on's file editor/Samba.
                "cleanup": False,
            },
        )
        if not result:
            logger.error("Honk! Upload failed for %r, skipping retention cleanup.", entry.title)
            continue
        _cleanup_old_editions(entry)
        _cleanup_local_editions(entry, output_path, out_dir)

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate and optionally deliver newspapers.")
    parser.add_argument(
        "--config", default="addon_config.json", help="Path to the addon config JSON file."
    )
    parser.add_argument("--output", default="output", help="Directory for generated PDFs.")
    parser.add_argument("--deliver", action="store_true", help="Upload to reMarkable after generating.")
    parser.add_argument("--newspaper", default=None, help="Only generate this newspaper id.")
    args = parser.parse_args(argv)
    return run(args.config, args.deliver, args.newspaper, args.output)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sys.exit(main())
