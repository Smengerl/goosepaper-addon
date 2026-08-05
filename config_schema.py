"""Pydantic models for the two-layer configuration this add-on uses.

Layer 1 - **addon config** (`AddonConfig`, loaded from `addon_config.json`): only what a
goosepaper config file can't express - a newspaper's id/title, its schedule, its reMarkable
folder, its retention policy, and which `*.goosepaper.json` file holds its actual content. This
is what the eventual Home Assistant add-on's own options hold.

Layer 2 - **goosepaper config** (`GoosepaperConfig`, one file per newspaper, referenced by path
from an `AddonNewspaperEntry`): the actual content - paper look (style/font/layout) and sections,
each with the sources that make it up. `content_skip_filters`/`skip_title_patterns` on an `"rss"`
source are native to the goosepaper-logicpuzzles fork's `RSSFeedStoryProvider` now (see
../goosepaper-logicpuzzles/goosepaper/storyprovider/rss.py) - they're validated and applied
there, not here; this file only has to know their shape well enough to pass them through
untouched.
"""

from __future__ import annotations

import json
import pathlib
from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    """Unknown fields (typos, stale keys) are a hard error instead of being silently dropped."""

    model_config = ConfigDict(extra="forbid")


# --- Sources (goosepaper-config layer) ----------------------------------------------------------


class ContentFilter(StrictModel):
    """One cleanup rule, applied natively by the fork's RSSFeedStoryProvider - see its own
    docstring/config.py validation for the authoritative behavior. Kept here only so this
    project's own schema can validate a goosepaper config file before handing it to the fork."""

    type: Literal["css", "regex"]
    selector: Optional[str] = None
    pattern: Optional[str] = None
    flags: str = ""

    @model_validator(mode="after")
    def _check_required_field(self) -> "ContentFilter":
        # selector/pattern/flags aren't a shared pool between the two types - each declared field
        # being individually optional (needed since one type requires it, the other forbids it)
        # means StrictModel's extra="forbid" alone can't catch e.g. a "css" filter that also sets
        # "pattern" (meant for "regex"); it's a legal field name, just wrong for this type.
        if self.type == "css":
            if not self.selector:
                raise ValueError("content_skip_filters: type 'css' requires a non-empty 'selector'")
            if self.pattern is not None or self.flags:
                raise ValueError("content_skip_filters: type 'css' does not accept 'pattern'/'flags'")
        if self.type == "regex":
            if not self.pattern:
                raise ValueError("content_skip_filters: type 'regex' requires a non-empty 'pattern'")
            if self.selector is not None:
                raise ValueError("content_skip_filters: type 'regex' does not accept 'selector'")
        return self


class ContentAcceptFilter(StrictModel):
    """One CSS-selector accept rule - narrows the article down to just this container instead of
    removing anything, applied natively by the fork. Only CSS is supported (see the fork's own
    contentfilters.py docstring): a regex accept would just reduce a story to whatever static
    phrase the pattern matches, not coherent prose, so there's no 'type' field here."""

    selector: str


class RSSSource(StrictModel):
    type: Literal["rss"] = "rss"
    name: str
    url: str
    limit: int = 5
    max_age_days: Optional[int] = None
    byline: Literal["all", "none", "first"] = "none"
    body_source: Literal["auto", "content", "summary", "article"] = "article"
    skip_title_patterns: List[str] = Field(default_factory=list)
    content_skip_filters: List[ContentFilter] = Field(default_factory=list)
    accept_title_patterns: List[str] = Field(default_factory=list)
    content_accept_filters: List[ContentAcceptFilter] = Field(default_factory=list)
    min_body_text_length: Optional[int] = None
    max_body_text_length: Optional[int] = None


class WikipediaSource(StrictModel):
    type: Literal["wikipedia"]
    name: str = "Wikipedia Top News"


class WeatherSource(StrictModel):
    type: Literal["weather"]
    name: str
    lat: float
    lon: float
    timezone: str = "Europe/Berlin"
    units: Literal["celsius", "fahrenheit"] = "celsius"
    mode: Literal["summary", "hourly", "daily", "hourly_daily"] = "daily"
    days: int = 3
    clock_format: Literal["12h", "24h"] = "24h"


class PuzzleSource(StrictModel):
    type: Literal["puzzle"]
    # No default beyond None: PuzzleStoryProvider treats "name given" vs. "name omitted" as two
    # genuinely different states (shown as this instance's own heading vs. nothing, relying on
    # the enclosing section's heading instead) - a string default here would silently always be
    # "given", so every puzzle without an explicit name would show that default text as if it
    # had been asked for. See goosepaper/storyprovider/puzzle.py's get_stories() docstring.
    name: Optional[str] = None
    # No default: the fork's PuzzleStoryProvider itself requires puzzle_type explicitly now
    # (a config that forgets it should fail loudly instead of silently always generating
    # Sudoku - see goosepaper/storyprovider/puzzle.py).
    puzzle_type: Literal["sudoku", "binoxxo", "futoshiki", "kakuro", "shikaku"]
    # Sudoku only; ignored for every other type. Supported: 2 (4x4) or 3 (the classic 9x9).
    box_size: int = 3
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    count: int = 1
    seed: Optional[int] = None
    explanation: Literal["none", "inline", "footer", "appendix"] = "none"


class ComicSource(StrictModel):
    type: Literal["comic"]
    comic_type: Literal["xkcd", "cah", "garfield"]


Source = Annotated[
    Union[RSSSource, WikipediaSource, WeatherSource, PuzzleSource, ComicSource],
    Field(discriminator="type"),
]


class Section(StrictModel):
    """A named group of sources, rendered together under one heading (goosepaper itself has no
    concept of sections - this wrapper adds it by tagging each Story.section_title, see
    deliver.py). Sources live directly inside their section - no cross-reference by name."""

    title: str
    sources: List[Source]

    @field_validator("sources", mode="before")
    @classmethod
    def _default_missing_type_to_rss(cls, value):
        if not isinstance(value, list):
            return value
        return [
            {"type": "rss", **item} if isinstance(item, dict) and "type" not in item else item
            for item in value
        ]


class PaperOptions(StrictModel):
    style: str = "FifthAvenue"
    font_size: int = 10
    page_profile: Literal[
        "remarkable1", "remarkable2", "paper_pro", "paper_pro_move", "letter", "a4"
    ] = "paper_pro"
    table_of_contents: bool = True
    layout: Literal["auto", "1col", "2col", "3col"] = "auto"


class Defaults(StrictModel):
    min_body_text_length: int = 120


class GoosepaperConfig(StrictModel):
    """The content of one `*.goosepaper.json` file: paper look + sections. No id/schedule/
    folder/retention here - those are addon-level, see `AddonNewspaperEntry`."""

    defaults: Defaults = Field(default_factory=Defaults)
    paper: PaperOptions = Field(default_factory=PaperOptions)
    sections: List[Section]


# --- Addon config layer --------------------------------------------------------------------------


class Retention(StrictModel):
    mode: Literal["keep_last_n", "keep_all"] = "keep_all"
    keep_last_n: Optional[int] = None

    @model_validator(mode="after")
    def _check_keep_last_n(self) -> "Retention":
        if self.mode == "keep_last_n" and not self.keep_last_n:
            raise ValueError("retention.keep_last_n is required when mode is 'keep_last_n'")
        return self


class AddonNewspaperEntry(StrictModel):
    id: str
    enabled: bool = True
    title: str
    schedule: str  # cron expression, e.g. "0 6 * * *" - passed straight to CronTrigger.from_crontab
    goosepaper_config: str  # path to the *.goosepaper.json file with this newspaper's content
    remarkable_folder: str
    retention: Retention = Field(default_factory=Retention)


class AddonConfig(StrictModel):
    newspapers: List[AddonNewspaperEntry]


def load_addon_config(path: str | pathlib.Path) -> AddonConfig:
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return AddonConfig.model_validate(data)


def load_goosepaper_config(path: str | pathlib.Path) -> GoosepaperConfig:
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return GoosepaperConfig.model_validate(data)


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
