"""Multi-newspaper generator + reMarkable uploader, driven by a two-layer config
(config_schema.py): `addon_config.json` (schedule/folder/retention/which content file - what
will eventually be this add-on's own options) plus one `*.goosepaper.json` file per newspaper
(sections/sources/paper look - the actual content, editable without touching addon options).

Depends on the goosepaper-logicpuzzles fork (see pyproject.toml, pinned to its `mainline`
branch) instead of the PyPI `goosepaper` package. Sections, RSS content/title filtering,
min/max body-length, feed-title preference, cross-source deduplication, and clean PDF bookmark
levels all used to be monkeypatches or wrapper classes here; they're now native fork features
(RSSFeedStoryProvider params, SectionProvider, Goosepaper(deduplicate=...), to_pdf(...)'s
bookmark-level params) - see the fork's own PRs for the rationale behind each.

What's left as a genuine wrapper concern:
1. remarkapy reads the account's sync `schemaVersion` from the root manifest and reuses it for
   writes. This account's is reported as schema 3, and gets rejected by the cloud on every write
   ("Software must be updated" / update-required) even though the server accepts schema-4 writes
   just fine - force schema 4. Reported upstream as
   https://github.com/j6k4m8/remarkapy/issues/24 (not a PR - forcing this unconditionally isn't
   verified safe for accounts that might still be genuinely write-limited to schema 3, only for
   this one). Revisit this patch once that's resolved - it may no longer be needed, or need a
   narrower condition than "always 4".
2. Translating this add-on's own config schema (config_schema.py) into fork constructor calls,
   grouped by section (_build_provider/_build_providers below).
"""

from __future__ import annotations

import argparse
import datetime
import logging
import pathlib
import sys
from typing import List, Optional

import remarkapy.client as _rc_client
from remarkapy.exceptions import RemarkableAPIError as _RemarkableAPIError

import config_schema

logger = logging.getLogger("goosepaper-addon")

# --- generic, always-on monkeypatches ----------------------------------------------------------

_original_get_root_state = _rc_client.Client.get_root_state


def _patched_get_root_state(self, refresh=False):
    root_hash, generation, _schema_version = _original_get_root_state(self, refresh=refresh)
    self._root_state = (root_hash, generation, 4)
    return self._root_state


_rc_client.Client.get_root_state = _patched_get_root_state


def auth_client():
    """Replaces goosepaper.auth.auth_client(), which builds its Client with remarkapy's
    interactive=True default: a missing device token then falls into an interactive input()
    pairing wizard instead of failing cleanly - harmless on a real terminal, but this container
    has no stdin, so that's an uncaught EOFError crash (seen in production logs) instead of the
    graceful "Honk! Authentication failed" every caller here already expects. scheduler.py's own
    startup check already goes through interactive=False; this makes every other reMarkable auth
    in the add-on do the same, so a token that goes missing mid-session (not just "never paired
    at startup") fails that one edition cleanly instead of crashing it.
    """
    try:
        client = _rc_client.Client(refresh_on_init=False, interactive=False)
        client.refresh_user_token()
        return client
    except _RemarkableAPIError as err:
        logger.error("Honk! reMarkable authentication failed: %s", err)
        return False


import goosepaper.auth as _gp_auth  # noqa: E402
import goosepaper.upload as _gp_upload  # noqa: E402

# goosepaper.upload.upload() (imported below) resolves auth_client via its own `from .auth
# import auth_client` binding, independent of this module's - patch both module-level names so
# every call site (this file's own _cleanup_old_editions, and upload() internally) gets the
# non-interactive version above instead of goosepaper's original.
_gp_auth.auth_client = auth_client
_gp_upload.auth_client = auth_client

from goosepaper.goosepaper import Goosepaper  # noqa: E402
from goosepaper.storyprovider.comic import DailyComicStoryProvider  # noqa: E402
from goosepaper.storyprovider.puzzle import PuzzleStoryProvider  # noqa: E402
from goosepaper.storyprovider.rss import RSSFeedStoryProvider  # noqa: E402
from goosepaper.storyprovider.section import SectionProvider  # noqa: E402
from goosepaper.storyprovider.storyprovider import StoryProvider  # noqa: E402
from goosepaper.storyprovider.weather import OpenMeteoWeatherStoryProvider  # noqa: E402
from goosepaper.storyprovider.wikipedia import (  # noqa: E402
    WikipediaCurrentEventsStoryProvider,
)
from goosepaper.upload import upload as goosepaper_upload  # noqa: E402


# --- per-source, config-driven provider construction ---------------------------------------------


def _build_provider(source: config_schema.Source, section_title: str) -> StoryProvider:
    if source.type == "rss":
        inner = RSSFeedStoryProvider(
            rss_path=source.url,
            limit=source.limit,
            since_days_ago=source.max_age_days,
            byline=source.byline,
            body_source=source.body_source,
            skip_content_filters=[
                f.model_dump(exclude_none=True) for f in source.content_skip_filters
            ],
            skip_title_patterns=source.skip_title_patterns,
            # ContentAcceptFilter is CSS-only (no "type" field, see config_schema.py) - the fork's
            # accept_content_filters entries need one to tell a css narrow-down from a regex gate.
            accept_content_filters=[
                {"type": "css", **f.model_dump(exclude_none=True)}
                for f in source.content_accept_filters
            ],
            accept_title_patterns=source.accept_title_patterns,
            min_body_text_length=source.min_body_text_length,
            max_body_text_length=source.max_body_text_length,
            # readability's own title extraction is unreliable on some sites (e.g. it returns
            # just the site name for every Golem article); the feed's own title is always
            # accurate, so always prefer it rather than making this a per-source config option.
            prefer_feed_title=True,
        )
        return SectionProvider(inner, section_title)
    if source.type == "wikipedia":
        return SectionProvider(WikipediaCurrentEventsStoryProvider(), section_title)
    if source.type == "weather":
        return SectionProvider(
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
        return SectionProvider(PuzzleStoryProvider(**kwargs), section_title)
    if source.type == "comic":
        return SectionProvider(
            DailyComicStoryProvider(comic_type=source.comic_type), section_title
        )
    raise ValueError(f"Unknown source type {source.type!r}")


def _build_providers(
    goosepaper_config: config_schema.GoosepaperConfig,
) -> List[StoryProvider]:
    providers = []
    for section in goosepaper_config.sections:
        for source in section.sources:
            providers.append(_build_provider(source, section.title))
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
    paper = Goosepaper(story_providers=providers, title=entry.title, deduplicate=True)

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

    newspapers = [n for n in addon_config.newspapers if n.enabled]
    if newspaper_id:
        newspapers = [n for n in newspapers if n.id == newspaper_id]
        if not newspapers:
            logger.error("Honk! No enabled newspaper with id %r found.", newspaper_id)
            return 1

    out_dir = pathlib.Path(output_dir)
    for entry in newspapers:
        config_path = config_schema.resolve_goosepaper_config_path(addon_config_path, entry)
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
