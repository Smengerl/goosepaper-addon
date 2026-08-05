"""Pydantic models for the add-on's own config layer: `addon_config.json` - one entry per
newspaper, with its schedule, reMarkable folder, retention policy, and which `*.goosepaper.json`
file holds its actual content.

The `*.goosepaper.json` files themselves are no longer parsed here - they're loaded directly by
goosepaper's own `load_paper_config()` (see deliver.py) and turned into story providers by its
own `construct_story_providers_from_source_configs()`. This add-on used to carry a full parallel
schema for that layer (source types, content filters, paper look, "sections" grouping) because
goosepaper's own declarative config format couldn't express several of those things at all -
`min_body_text_length`/`max_body_text_length`, a "section" tag, and this add-on's own retention
concept were all addon-only inventions at the time. Those gaps are closed upstream now (see
mainline's README "About this fork" table for the PRs), so this add-on delegates instead of
duplicating - not just because it's less code, but because a change to what a `.goosepaper.json`
file can express should only need to happen in one place, not here and in the fork.
"""

from __future__ import annotations

import json
import pathlib
from typing import Optional

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Unknown fields (typos, stale keys) are a hard error instead of being silently dropped."""

    model_config = ConfigDict(extra="forbid")


class AddonNewspaperEntry(StrictModel):
    id: str
    enabled: bool = True
    title: str
    schedule: str  # cron expression, e.g. "0 6 * * *" - passed straight to CronTrigger.from_crontab
    goosepaper_config: str  # path to the *.goosepaper.json file with this newspaper's content
    remarkable_folder: str
    # None = no retention (upload() gets called without retention_keep_last_n/retention_prefix,
    # see deliver.py). Matches goosepaper's own DeliverySettings.retention_keep_last_n exactly -
    # deliberately not a separate mode enum + count pair the way this field used to be modeled:
    # an Optional[int] already fully encodes "on" vs. "off" on its own, the same way
    # min_body_text_length/max_body_text_length already do.
    retention_keep_last_n: Optional[int] = None


class AddonConfig(StrictModel):
    newspapers: list[AddonNewspaperEntry]


def load_addon_config(path: str | pathlib.Path) -> AddonConfig:
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return AddonConfig.model_validate(data)


def resolve_goosepaper_config_path(
    addon_config_path: str | pathlib.Path, entry: AddonNewspaperEntry
) -> pathlib.Path:
    """`entry.goosepaper_config` is normally a bare filename, resolved relative to
    `addon_config_path`'s own directory - both deliver.py (to actually load it) and scheduler.py
    (to show it in the startup overview log) need this exact same resolution, so it lives here
    once instead of twice."""
    config_path = pathlib.Path(entry.goosepaper_config)
    if config_path.is_absolute():
        return config_path
    return pathlib.Path(addon_config_path).resolve().parent / config_path
