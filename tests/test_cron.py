import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cron  # noqa: E402

# 2026-10-12 is a Monday.
MONDAY = datetime(2026, 10, 12, 12, 0)


def _fire_weekdays(schedule: str, days: int = 14) -> set[str]:
    """Weekday names the schedule fires on in the two weeks after MONDAY."""
    trigger = cron.trigger_from_crontab(schedule)
    tz = trigger.timezone
    now = MONDAY.replace(tzinfo=tz)
    end = now + timedelta(days=days)
    seen = set()
    while True:
        now = trigger.get_next_fire_time(None, now)
        if now is None or now >= end:
            break
        seen.add(now.strftime("%a").lower())
        now += timedelta(seconds=1)
    return seen


@pytest.mark.parametrize(
    "field, expected",
    [
        ("*", {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}),
        ("0", {"sun"}),
        ("7", {"sun"}),
        ("1", {"mon"}),
        ("6", {"sat"}),
        ("1-5", {"mon", "tue", "wed", "thu", "fri"}),
        ("1,3,5", {"mon", "wed", "fri"}),
        ("6,0", {"sat", "sun"}),
        ("6-7", {"sat", "sun"}),
        ("*/2", {"sun", "tue", "thu", "sat"}),
        ("1-5/2", {"mon", "wed", "fri"}),
        ("mon", {"mon"}),
        ("Mon-Fri", {"mon", "tue", "wed", "thu", "fri"}),
        ("sat-sun", {"sat", "sun"}),
        ("fri-mon", {"fri", "sat", "sun", "mon"}),
    ],
)
def test_day_of_week_follows_standard_cron(field, expected):
    assert _fire_weekdays(f"0 4 * * {field}") == expected


@pytest.mark.parametrize("schedule", ["0 4 * *", "0 4 * * * *", "", "0 4 * * 8", "0 4 * * foo", "0 4 * * 1-x", "0 4 * * 1/0"])
def test_invalid_schedules_are_rejected(schedule):
    with pytest.raises(ValueError):
        cron.trigger_from_crontab(schedule)


def test_other_fields_are_unchanged():
    trigger = cron.trigger_from_crontab("30 6 15 * *")
    nxt = trigger.get_next_fire_time(None, MONDAY.replace(tzinfo=trigger.timezone))
    assert (nxt.day, nxt.hour, nxt.minute) == (15, 6, 30)
