"""What's left of the old content-filter engine after `content_skip_filters`/`skip_title_patterns`
moved into the goosepaper-fork's RSSFeedStoryProvider natively (see ../goosepaper-fork). Only the
minimum-body-length safety net stays a wrapper-level concern: it's a cross-provider policy (an
optional per-source override falling back to a newspaper-wide default), not something a single
source's own config can express.
"""

from __future__ import annotations

import re


def visible_text_length(html: str) -> int:
    return len(re.sub(r"<[^>]+>", " ", html or "").strip())
