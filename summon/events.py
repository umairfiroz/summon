"""Event model, validation and recurrence. No AI and no UI in this module.

An event repeats in one of three ways:
* "none"           - happens once, on `date`.
* "weekly"         - every week on `date`'s weekday, until `until` (inclusive).
* "teaching_weeks" - on `weekday` in the listed university teaching weeks, counted
                     from the Monday of week 1 (supplied by the user).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
REPEATS = {"none": "Doesn't repeat", "weekly": "Every week", "teaching_weeks": "Teaching weeks"}
KINDS = {"event": "Event", "deadline": "Deadline"}
MAX_WEEK = 60
DEFAULT_LENGTH = timedelta(hours=1)


@dataclass
class Event:
    id: int
    title: str = ""
    kind: str = "event"                  # "event" | "deadline"
    date: date | None = None
    start: time | None = None
    end: time | None = None
    all_day: bool = False
    location: str = ""
    notes: str = ""
    repeat: str = "none"                 # see module docstring
    until: date | None = None            # for "weekly"
    weekday: int | None = None           # 0 = Monday, for "teaching_weeks"
    weeks: str = ""                      # e.g. "1-10, 12", for "teaching_weeks"
    reminder: int | None = None          # minutes before; None = no reminder
    include: bool = True
    unclear: str | None = None           # reason given by Gemma, shown to the user
    notes_from_import: list[str] = field(default_factory=list)


def parse_weeks(text: str) -> list[int]:
    """'1-10, 12' -> [1, ..., 10, 12]. Raises ValueError with a readable message."""
    if not text or not text.strip():
        raise ValueError("Enter the teaching weeks, for example 1-10, 12.")
    weeks: set[int] = set()
    for part in re.split(r"[,;]", text):
        part = part.strip().lower().removeprefix("weeks").removeprefix("week").removeprefix("wk").strip()
        if not part:
            continue
        match = re.fullmatch(r"(\d+)\s*(?:-|–|to)\s*(\d+)", part)
        if match:
            first, last = int(match.group(1)), int(match.group(2))
            if first > last:
                raise ValueError(f"“{part}” goes backwards. Write the smaller week first.")
            weeks.update(range(first, last + 1))
        elif part.isdigit():
            weeks.add(int(part))
        else:
            raise ValueError(f"“{part}” isn't a week number or range. Use a format like 1-10, 12.")
    if not weeks:
        raise ValueError("Enter the teaching weeks, for example 1-10, 12.")
    if min(weeks) < 1 or max(weeks) > MAX_WEEK:
        raise ValueError(f"Week numbers must be between 1 and {MAX_WEEK}.")
    return sorted(weeks)


def format_weeks(weeks: list[int]) -> str:
    """[1,2,3,5] -> '1-3, 5'."""
    if not weeks:
        return ""
    ranges, start, prev = [], weeks[0], weeks[0]
    for w in weeks[1:] + [None]:
        if w is not None and w == prev + 1:
            prev = w
            continue
        ranges.append(str(start) if start == prev else f"{start}-{prev}")
        if w is not None:
            start = prev = w
    return ", ".join(ranges)


def occurrence_dates(event: Event, week1: date | None) -> list[date]:
    """Every date the event happens on. Raises ValueError if it can't be worked out."""
    if event.repeat == "teaching_weeks":
        if week1 is None:
            raise ValueError("Set the date week 1 starts on.")
        if week1.weekday() != 0:
            raise ValueError("Week 1 must start on a Monday.")
        if event.weekday is None:
            raise ValueError("Choose the day of the week.")
        return [week1 + timedelta(weeks=w - 1, days=event.weekday) for w in parse_weeks(event.weeks)]
    if event.date is None:
        raise ValueError("Add a date.")
    if event.repeat == "weekly":
        if event.until is None:
            raise ValueError("Choose when the weekly repeat ends.")
        if event.until < event.date:
            raise ValueError("The repeat must end on or after the first date.")
        dates, current = [], event.date
        while current <= event.until:
            dates.append(current)
            current += timedelta(weeks=1)
        return dates
    return [event.date]


def problems(event: Event, week1: date | None) -> list[str]:
    """Everything that stops this event being exported, in plain words."""
    found = []
    if not event.title.strip():
        found.append("Add a title.")
    try:
        occurrence_dates(event, week1)
    except ValueError as exc:
        found.append(str(exc))
    if not event.all_day:
        if event.start is None:
            found.append("Add a start time, or mark it as all day.")
        elif event.kind == "event" and event.end is not None and event.end <= event.start:
            found.append("The end time must be after the start time.")
    return found


def end_time(event: Event) -> time | None:
    """End time used for export: the given end, or one hour after the start for events."""
    if event.all_day or event.start is None or event.kind == "deadline":
        return None
    if event.end is not None:
        return event.end
    finish = datetime.combine(date(2000, 1, 1), event.start) + DEFAULT_LENGTH
    return finish.time() if finish.date() == date(2000, 1, 1) else time(23, 59)


def nice_date(d: date) -> str:
    """'Fri 30 Oct 2026' (portable: %-d doesn't work on Windows)."""
    return f"{d:%a} {d.day} {d:%b %Y}"


def describe_when(event: Event, week1: date | None) -> str:
    """Short human summary, e.g. 'Mon 09:00-11:00 · weeks 1-10, 12 (11 times)'."""
    if event.all_day:
        clock = "all day"
    elif event.start is None:
        clock = "time missing"
    elif event.kind == "deadline":
        clock = f"due {event.start:%H:%M}"
    else:
        clock = f"{event.start:%H:%M}–{end_time(event):%H:%M}"
    try:
        dates = occurrence_dates(event, week1)
    except ValueError:
        dates = []
    if event.repeat == "teaching_weeks":
        day = WEEKDAYS[event.weekday][:3] if event.weekday is not None else "Day?"
        try:
            weeks = format_weeks(parse_weeks(event.weeks))
        except ValueError:
            weeks = event.weeks or "?"
        count = f" ({len(dates)} times)" if dates else ""
        return f"{day} {clock} · weeks {weeks}{count}"
    if event.date is None:
        return f"Date missing · {clock}"
    first = nice_date(event.date)
    if event.repeat == "weekly" and dates:
        return f"{first} · {clock} · weekly until {event.until.day} {event.until:%b} ({len(dates)} times)"
    return f"{first} · {clock}"
