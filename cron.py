"""Cron-expression handling for newspaper schedules.

`schedule` in addon_config.json is a classic five-field cron expression
(`minute hour day-of-month month day-of-week`). APScheduler's own `CronTrigger.from_crontab`
passes the day-of-week field through untranslated, but APScheduler numbers weekdays
0 = Monday ... 6 = Sunday, whereas standard cron (crontab(5)) numbers them
0 = Sunday, 1 = Monday ... 6 = Saturday, with 7 also meaning Sunday. So `0 4 * * 1` - "Mondays at
04:00" in every crontab tutorial - would have run on Tuesdays.

`trigger_from_crontab` fixes that by reading the field with standard cron meaning and handing
APScheduler weekday *names* (mon, tue, ...), which both sides agree on.
"""

from __future__ import annotations

from apscheduler.triggers.cron import CronTrigger

# Standard cron order: index == cron's number for that day (0 = Sunday).
_DAY_NAMES = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]


def _day_number(token: str, schedule: str) -> int:
    token = token.strip().lower()
    if token.isdigit():
        number = int(token)
        if 0 <= number <= 7:
            return number
    elif token in _DAY_NAMES:
        return _DAY_NAMES.index(token)
    raise ValueError(
        f"Invalid day of week {token!r} in schedule {schedule!r}: use 0-7 "
        f"(0 and 7 = Sunday, 1 = Monday) or mon, tue, wed, thu, fri, sat, sun."
    )


def translate_day_of_week(field: str, schedule: str = "") -> str:
    """Standard-cron day-of-week field -> APScheduler day-of-week field (weekday names)."""
    if field in ("*", "?"):
        return "*"

    days: set[int] = set()
    for part in field.split(","):
        range_part, has_step, step_part = part.partition("/")
        if has_step:
            if not step_part.isdigit() or int(step_part) < 1:
                raise ValueError(f"Invalid step {step_part!r} in schedule {schedule!r}.")
            step = int(step_part)
        else:
            step = 1

        if range_part in ("*", "?"):
            first, last = 0, 6
        elif "-" in range_part:
            low, high = range_part.split("-", 1)
            first, last = _day_number(low, schedule), _day_number(high, schedule)
            if last < first:  # wrap-around such as fri-mon or sat-sun
                last += 7
        else:
            first = last = _day_number(range_part, schedule)
            if has_step:  # "1/2" means "from 1 to the end of the week, every 2nd"
                last = 6 if first < 7 else 7

        days.update(day % 7 for day in range(first, last + 1, step))

    return ",".join(_DAY_NAMES[day] for day in sorted(days))


def trigger_from_crontab(schedule: str) -> CronTrigger:
    """Build a CronTrigger from a standard five-field cron expression."""
    fields = schedule.split()
    if len(fields) != 5:
        raise ValueError(
            f"Invalid schedule {schedule!r}: expected 5 fields "
            f"(minute hour day-of-month month day-of-week), got {len(fields)}."
        )
    minute, hour, day, month, day_of_week = fields
    return CronTrigger(
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=translate_day_of_week(day_of_week, schedule),
    )
