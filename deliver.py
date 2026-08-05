"""Multi-newspaper generator + reMarkable uploader, driven by `addon_config.json` (schedule/
folder/retention/which content file). Each `*.goosepaper.json` file is loaded and turned into
story providers entirely by goosepaper itself (`load_paper_config()` +
`construct_story_providers_from_source_configs()`), not by this add-on's own schema - see
config_schema.py's module docstring for why.

Depends on the goosepaper-logicpuzzles fork (see pyproject.toml, pinned to its `mainline`
branch) instead of the PyPI `goosepaper` package - the whole point of the fork is to get gaps
like the ones above fixed upstream (see mainline's README's "About this fork" PR-tracking table)
rather than staying addon-only forever; this file only carries what's genuinely HA/Supervisor-
specific.

What's left as a genuine wrapper concern:
1. remarkapy reads the account's sync `schemaVersion` from the root manifest and reuses it for
   writes. This account's is reported as schema 3, and gets rejected by the cloud on every write
   ("Software must be updated" / update-required) even though the server accepts schema-4 writes
   just fine - force schema 4. Reported upstream as
   https://github.com/j6k4m8/remarkapy/issues/24 (not a PR - forcing this unconditionally isn't
   verified safe for accounts that might still be genuinely write-limited to schema 3, only for
   this one). Revisit this patch once that's resolved - it may no longer be needed, or need a
   narrower condition than "always 4".
2. Turning `addon_config.json`'s per-newspaper entries (schedule/folder/retention/which
   `*.goosepaper.json` file) into calls against goosepaper's own `Goosepaper`/`upload()` - the
   multi-newspaper orchestration layer goosepaper itself doesn't have (it's designed around one
   config file per invocation).
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

logger = logging.getLogger("goosepaper-addon")

# --- generic, always-on monkeypatch ------------------------------------------------------------
# Still needed - see module docstring, point 1 (https://github.com/j6k4m8/remarkapy/issues/24).
# The interactive=True default that used to need patching here too (goosepaper.auth.auth_client,
# goosepaper.upload.auth_client) is now a real parameter on goosepaper's own auth_client()/
# upload() (PR #137) - passed as interactive=False at the two call sites below instead.

_original_get_root_state = _rc_client.Client.get_root_state


def _patched_get_root_state(self, refresh=False):
    root_hash, generation, _schema_version = _original_get_root_state(self, refresh=refresh)
    self._root_state = (root_hash, generation, 4)
    return self._root_state


_rc_client.Client.get_root_state = _patched_get_root_state


from goosepaper.config import load_paper_config  # noqa: E402
from goosepaper.goosepaper import Goosepaper  # noqa: E402
from goosepaper.upload import upload as goosepaper_upload  # noqa: E402
from goosepaper.util import construct_story_providers_from_source_configs  # noqa: E402


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
    goosepaper_config,
    output_dir: pathlib.Path,
) -> pathlib.Path:
    providers = construct_story_providers_from_source_configs(goosepaper_config.sources)
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
            goosepaper_config = load_paper_config(config_path)
        except Exception as err:
            logger.error("Honk! Could not load %s for %r: %s", config_path, entry.title, err)
            continue

        logger.info("Honk! Generating %r (from %s)...", entry.title, config_path)
        output_path = _generate_newspaper(entry, goosepaper_config, out_dir)
        logger.info("Honk! Wrote %s", output_path)

        if not deliver:
            continue

        retention_keep_last_n = (
            entry.retention.keep_last_n if entry.retention.mode == "keep_last_n" else None
        )
        result = goosepaper_upload(
            filepath=str(output_path),
            delivery_settings={
                "folder": entry.remarkable_folder,
                "replace_mode": "nocase",
                # Left off deliberately: the local file is kept (see _cleanup_local_editions
                # below), not removed the instant it's uploaded, so the last generated edition
                # stays inspectable in output/ - e.g. via the HA add-on's file editor/Samba.
                "cleanup": False,
                "retention_keep_last_n": retention_keep_last_n,
                "retention_prefix": f"{entry.title} " if retention_keep_last_n else None,
            },
            interactive=False,
        )
        if not result:
            logger.error("Honk! Upload failed for %r.", entry.title)
            continue
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
