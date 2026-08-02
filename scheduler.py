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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("goosepaper-addon")

ADDON_CONFIG_PATH = os.environ.get("ADDON_CONFIG", "/config/addon_config.json")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/data/output")
EXAMPLES_DIR = pathlib.Path(__file__).resolve().parent / "examples"
OPTIONS_PATH = pathlib.Path("/data/options.json")


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
    try:
        options = json.loads(OPTIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return (options.get("remarkable_pairing_code") or "").strip()


def _check_and_complete_remarkable_pairing() -> None:
    """Startup diagnostic + optional self-service pairing, so a missing/broken pairing shows up
    immediately in the logs instead of surfacing as a silent upload failure days later. Never
    blocks startup - RSS/puzzle generation works fine without pairing, only delivery needs it -
    and catches broadly, not just auth errors, since a network hiccup at boot (reMarkable
    unreachable, DNS not up yet) must not crash the add-on either.

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
        return
    except ConfigNotFoundError:
        pass
    except Exception as err:
        logger.warning(
            "Honk! reMarkable pairing exists but couldn't be verified (%s) - delivery may fail "
            "until you re-pair.",
            err,
        )
        return

    code = _read_pairing_code_option()
    if not code:
        logger.warning(
            "Honk! No reMarkable pairing found - newspapers will still generate, but delivery "
            "will fail. Pair via Settings -> Add-ons -> Goosepaper -> Configuration "
            "(remarkable_pairing_code, get one from https://my.remarkable.com/pair/app), or run "
            "'remarkapy init' in the add-on's shell."
        )
        return

    try:
        client.register_device(code)
        logger.info("Honk! reMarkable pairing complete via the configured pairing code.")
    except Exception as err:
        logger.warning(
            "Honk! reMarkable pairing failed with the configured code (%s) - get a fresh code "
            "from https://my.remarkable.com/pair/app and update it under Settings -> Add-ons -> "
            "Goosepaper -> Configuration.",
            err,
        )


def _run_newspaper(newspaper_id: str) -> None:
    logger.info("Honk! Triggering scheduled generation for %r", newspaper_id)
    try:
        deliver.run(ADDON_CONFIG_PATH, True, newspaper_id, OUTPUT_DIR)
    except Exception:
        logger.exception("Honk! Scheduled run failed for %r", newspaper_id)


def main() -> int:
    _seed_default_config()
    _check_and_complete_remarkable_pairing()

    try:
        addon_config = config_schema.load_addon_config(ADDON_CONFIG_PATH)
    except Exception as err:
        logger.error("Honk! Could not load %s: %s", ADDON_CONFIG_PATH, err)
        return 1

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
