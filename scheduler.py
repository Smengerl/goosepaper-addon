"""Container entrypoint: schedules `deliver.run()` once per enabled newspaper, on its own
`schedule` cron string from addon_config.json, and blocks forever. Each newspaper's own
goosepaper config is reloaded from disk on every run, so editing a `*.goosepaper.json` file takes
effect on the next scheduled edition - only a schedule/id/enabled change in addon_config.json
itself needs a container restart to pick up, since the job list is built once at startup.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import shutil
import signal

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from remarkapy.client import Client
from remarkapy.exceptions import ConfigNotFoundError

import config_schema
import deliver

logger = logging.getLogger("goosepaper-addon")

ADDON_CONFIG_PATH = os.environ.get("ADDON_CONFIG", "/config/addon_config.json")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/data/output")
EXAMPLES_DIR = pathlib.Path(__file__).resolve().parent / "examples"
OPTIONS_PATH = pathlib.Path("/data/options.json")

_LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def _read_options() -> dict:
    try:
        return json.loads(OPTIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _read_generation_log_level_option() -> int:
    raw = str(_read_options().get("generation_log_level") or "warning").strip().lower()
    return _LOG_LEVELS.get(raw, logging.WARNING)


def _configure_logging() -> None:
    """A goosepaper edition pulls in WeasyPrint (which logs every fontTools subsetting step),
    httpx (which logs every HTTP request), APScheduler's own job-lifecycle chatter, and more -
    all at INFO, all sharing the root logger with this add-on's own "Honk!" messages. Left alone,
    that noise buries the messages that actually matter (a schedule firing, the configured-
    newspapers overview, pairing status) under dozens of "glyf pruned"-style lines per edition.

    generation_log_level (an add-on option, see config.yaml) sets the root logger's level, so it
    controls everything BUT this add-on's own logger - that's pinned to INFO immediately after,
    regardless of the option, so turning generation noise down can never hide an add-on-level
    message. Set it to "debug" temporarily when actually troubleshooting generation itself.
    """
    logging.basicConfig(
        level=_read_generation_log_level_option(),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logger.setLevel(logging.INFO)


def _seed_default_config() -> None:
    """First-run convenience: an empty /config volume (a fresh install) would otherwise just
    error out until someone manually copies files in. Seed it from the sanitized examples/ - baked
    into the image, see Dockerfile - so the add-on produces a working edition immediately. Never
    overwrites: only runs when addon_config.json doesn't exist yet."""
    config_path = pathlib.Path(ADDON_CONFIG_PATH)
    if config_path.exists() or not EXAMPLES_DIR.is_dir():
        return
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        for src in EXAMPLES_DIR.iterdir():
            name = "addon_config.json" if src.name == "addon_config.example.json" else src.name
            shutil.copy2(src, config_path.parent / name)
    except OSError as err:
        logger.warning("Honk! Could not seed default config at %s: %s", config_path.parent, err)
        return
    logger.info(
        "Honk! No %s found - seeded /config with the example newspapers from examples/. Edit "
        "them (feeds, reMarkable folder, coordinates) to make them yours.",
        ADDON_CONFIG_PATH,
    )


def _read_pairing_code_option() -> str:
    return (_read_options().get("remarkable_pairing_code") or "").strip()


def _check_and_complete_remarkable_pairing() -> bool:
    """Startup diagnostic + optional self-service pairing, so a missing/broken pairing shows up
    immediately in the logs instead of surfacing as a silent upload failure days later, and so no
    cron jobs get scheduled against a delivery that can only fail. Returns False only when there
    is truly no usable pairing - no existing token and no working pairing code - in which case the
    caller refuses to start rather than schedule newspapers that would just fail on delivery.

    A transient verification error against an *already-paired* token (e.g. reMarkable unreachable,
    DNS not up yet at boot) does NOT block startup - that's a network hiccup, not a pairing
    problem, and treating it as fatal would crash-loop the add-on. Returns True in that case, same
    as a fully verified pairing.

    If a `remarkable_pairing_code` add-on option is set (Settings -> Add-ons -> Goosepaper ->
    Configuration - the GUI alternative to shelling in and running `remarkapy init`) and no
    valid pairing exists yet, uses it to complete pairing directly; `register_device()` is the
    same call the interactive wizard makes after reading its code from stdin, just driven from
    the option instead. A stale/already-used code just fails safely on every restart until the
    field is updated - once truly paired, the verification above succeeds first and the option
    is never consulted again.
    """
    client = Client(refresh_on_init=False, interactive=False)
    try:
        client.refresh_user_token()
        logger.info("Honk! reMarkable pairing verified.")
        return True
    except ConfigNotFoundError:
        pass
    except Exception as err:
        logger.warning(
            "Honk! reMarkable pairing exists but couldn't be verified (%s) - delivery may fail "
            "until you re-pair.",
            err,
        )
        return True

    code = _read_pairing_code_option()
    if not code:
        logger.error(
            "Honk! No reMarkable pairing found - refusing to start, since scheduled newspapers "
            "would only fail on delivery. Pair via Settings -> Add-ons -> Goosepaper -> "
            "Configuration (remarkable_pairing_code, get one from "
            "https://my.remarkable.com/pair/app), or run 'remarkapy init' in the add-on's shell, "
            "then restart the add-on."
        )
        return False

    try:
        client.register_device(code)
        logger.info("Honk! reMarkable pairing complete via the configured pairing code.")
        return True
    except Exception as err:
        logger.error(
            "Honk! reMarkable pairing failed with the configured code (%s) - refusing to start. "
            "Get a fresh code from https://my.remarkable.com/pair/app and update it under "
            "Settings -> Add-ons -> Goosepaper -> Configuration, then restart the add-on.",
            err,
        )
        return False


def _run_newspaper(newspaper_id: str) -> None:
    logger.info("Honk! Triggering scheduled generation for %r", newspaper_id)
    try:
        deliver.run(ADDON_CONFIG_PATH, True, newspaper_id, OUTPUT_DIR)
        logger.info("Honk! Finished scheduled generation for %r", newspaper_id)
    except Exception:
        logger.exception("Honk! Scheduled run failed for %r", newspaper_id)


def _describe_retention(retention: config_schema.Retention) -> str:
    if retention.mode == "keep_last_n":
        return f"keep last {retention.keep_last_n}"
    return "keep all"


def _last_local_edition(title: str, output_dir: pathlib.Path) -> str:
    matches = sorted(output_dir.glob(f"{title} *.pdf"))
    return matches[-1].name if matches else "none yet"


def _log_newspaper_overview(addon_config: config_schema.AddonConfig, output_dir: pathlib.Path) -> None:
    """Read-only overview of the current addon_config.json, logged once at startup so 'what's
    configured, and does it look right' is visible from the Log tab without needing a file editor
    - see DOCS.md's "Editing your configuration" section for actually changing any of this. The
    'last local edition' column reads output_dir's filenames rather than tracking its own state,
    since deliver.py already keeps exactly the latest PDF per newspaper there (see
    _cleanup_local_editions) - no separate state file to keep in sync.
    """
    logger.info("Honk! Configured newspapers (%d), read from %s:", len(addon_config.newspapers), ADDON_CONFIG_PATH)
    for entry in addon_config.newspapers:
        status = "enabled" if entry.enabled else "disabled"
        logger.info(
            "Honk!   - %s %r - %s, cron %r, config %s, folder %r, retention: %s, "
            "last local edition: %s",
            entry.id,
            entry.title,
            status,
            entry.schedule,
            config_schema.resolve_goosepaper_config_path(ADDON_CONFIG_PATH, entry),
            entry.remarkable_folder,
            _describe_retention(entry.retention),
            _last_local_edition(entry.title, output_dir),
        )
    logger.info(
        "Honk! Note: each newspaper's own *.goosepaper.json (the 'config' column above) is "
        "reloaded fresh on every scheduled run, so editing sections/sources/paper look takes "
        "effect immediately, no restart needed. Changing %s itself - schedule, id, enabled, "
        "adding/removing a newspaper - needs an add-on restart to take effect, since the job "
        "list above is only built once at startup.",
        ADDON_CONFIG_PATH,
    )


def main() -> int:
    _configure_logging()
    _seed_default_config()
    if not _check_and_complete_remarkable_pairing():
        return 1

    try:
        addon_config = config_schema.load_addon_config(ADDON_CONFIG_PATH)
    except Exception as err:
        logger.error("Honk! Could not load %s: %s", ADDON_CONFIG_PATH, err)
        return 1
    _log_newspaper_overview(addon_config, pathlib.Path(OUTPUT_DIR))

    scheduler = BlockingScheduler()

    def _handle_shutdown(signum, frame):
        logger.info("Honk! Received signal %s, shutting down...", signum)
        scheduler.shutdown(wait=False)

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    for entry in addon_config.newspapers:
        if not entry.enabled:
            logger.info("Honk! Skipping disabled newspaper %r", entry.id)
            continue
        trigger = CronTrigger.from_crontab(entry.schedule)
        scheduler.add_job(_run_newspaper, trigger=trigger, args=[entry.id], id=entry.id, name=entry.title)
        logger.info("Honk! Scheduled %r (%s) -> cron %r", entry.title, entry.id, entry.schedule)

    if not scheduler.get_jobs():
        logger.warning(
            "Honk! No enabled newspapers found in %s - nothing to schedule.", ADDON_CONFIG_PATH
        )

    logger.info("Honk! Scheduler running, waiting for the next scheduled edition...")
    scheduler.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
