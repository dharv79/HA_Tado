"""Read-only schedule parsing: the next change of a classic zone's timetable."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

# Day types per timetable kind; keys are weekday() numbers (Monday = 0).
_WEEKDAYS = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")


def day_type(timetable_type: str, weekday: int) -> str:
    """Block ``dayType`` that applies on a weekday for a timetable type."""
    kind = timetable_type.upper()
    if kind == "ONE_DAY":
        return "MONDAY_TO_SUNDAY"
    if kind == "THREE_DAY":
        if weekday < 5:
            return "MONDAY_TO_FRIDAY"
        return _WEEKDAYS[weekday]
    return _WEEKDAYS[weekday]


def _clock(value: Any) -> tuple[int, int] | None:
    try:
        hour, minute = str(value).split(":")[:2]
        return int(hour), int(minute)
    except ValueError:
        return None


def _setting(block: dict[str, Any]) -> tuple[str | None, float | None]:
    setting = block.get("setting") or {}
    temp = (setting.get("temperature") or {}).get("celsius")
    return setting.get("power"), float(temp) if isinstance(temp, (int, float)) else None


def next_change(schedule: dict[str, Any] | None, now: datetime) -> dict[str, Any] | None:
    """First future block start whose setting differs from the one in force.

    ``schedule`` is ``{"type": <timetable type>, "blocks": [<block>, ...]}``;
    ``now`` must be timezone-aware in the home's time zone. Returns
    ``{"at", "power", "temperature"}`` or None when nothing is found within a week.
    """
    if not isinstance(schedule, dict):
        return None
    blocks = schedule.get("blocks")
    kind = str(schedule.get("type") or "")
    if not isinstance(blocks, list) or not kind:
        return None
    events: list[tuple[datetime, tuple[str | None, float | None]]] = []
    for offset in range(-1, 8):
        date = (now + timedelta(days=offset)).date()
        wanted = day_type(kind, date.weekday())
        for block in blocks:
            if not isinstance(block, dict) or block.get("dayType") != wanted:
                continue
            clock = _clock(block.get("start"))
            if clock is None:
                continue
            start = now.replace(
                year=date.year,
                month=date.month,
                day=date.day,
                hour=clock[0],
                minute=clock[1],
                second=0,
                microsecond=0,
            )
            events.append((start, _setting(block)))
    events.sort(key=lambda event: event[0])
    current = None
    for start, setting in events:
        if start <= now:
            current = setting
            continue
        if setting != current:
            power, temperature = setting
            return {"at": start, "power": power, "temperature": temperature}
    return None
