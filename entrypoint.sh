#!/usr/bin/env bash
# Generates the `locale` add-on option's value (if set) *before* starting scheduler.py, in this
# separate shell process rather than as a subprocess spawned from within scheduler.py itself.
#
# That split is required, not just tidier: verified empirically (see goosepaper-addon's AGENTS.md/
# commit history) that running `locale-gen` as a subprocess from a already-running Python process
# and then calling `locale.setlocale()` in that *same* process fails with "unsupported locale
# setting" even though the locale was genuinely generated (confirmed via `locale -a` and via a
# separate process picking it up fine right after) - some glibc-level locale-archive state gets
# cached per-process before the regeneration lands. Running locale-gen here, then `exec`-ing into
# python (a real process image replacement, not a subprocess call), gives scheduler.py a fresh
# process that has never touched locale machinery before its own `setlocale()` call - and that
# works reliably.
set -euo pipefail

locale_name="$(python3 -c '
import json
try:
    with open("/data/options.json", encoding="utf-8") as fh:
        print((json.load(fh).get("locale") or "").strip())
except Exception:
    print("")
')"

if [ -n "$locale_name" ]; then
    entry="${locale_name}.UTF-8 UTF-8"
    if ! grep -qxF "$entry" /etc/locale.gen 2>/dev/null; then
        echo "$entry" >> /etc/locale.gen
    fi
    # locale-gen exits 0 even for a bogus entry (verified: logs its own "[error] cannot open
    # locale definition file" but still reports "Generation complete") - deliver.configure_locale()
    # in scheduler.py is what actually surfaces an invalid `locale` option, via setlocale()
    # raising locale.Error. This is a last-resort net for locale-gen itself being unavailable.
    locale-gen || echo "Honk! locale-gen failed for '${locale_name}' - date stamps may fall back to the container default." >&2
fi

exec python scheduler.py
