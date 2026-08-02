"""Container entrypoint: schedules `deliver.run()` once per enabled newspaper, on its own
`schedule` cron string from addon_config.json, and blocks forever. Each newspaper's own
goosepaper config is reloaded from disk on every run, so editing a `*.goosepaper.json` file takes
effect on the next scheduled edition - only a schedule/id/enabled change in addon_config.json
itself needs a container restart to pick up, since the job list is built once at startup.
"""

from __future__ import annotations

import logging
import os
import signal

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import config_schema
import deliver

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("goosepaper-addon")

ADDON_CONFIG_PATH = os.environ.get("ADDON_CONFIG", "/config/addon_config.json")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/data/output")


def _run_newspaper(newspaper_id: str) -> None:
    logger.info("Honk! Triggering scheduled generation for %r", newspaper_id)
    try:
        deliver.run(ADDON_CONFIG_PATH, True, newspaper_id, OUTPUT_DIR)
    except Exception:
        logger.exception("Honk! Scheduled run failed for %r", newspaper_id)


def main() -> int:
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
