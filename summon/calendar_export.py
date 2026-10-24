"""Turn events into a standard .ics calendar file and 'Add to Google Calendar' links.

Times are written in the user's time zone with a VTIMEZONE block, so repeating
events stay at the same local time across daylight-saving changes.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from icalendar import Alarm, Calendar
from icalendar import Event as VEvent

from .events import Event, end_time, occurrence_dates

PRODID = "-//Summon//Summon calendar export//EN"


def _uid(event: Event, first: date) -> str:
    seed = f"{event.title}|{first.isoformat()}|{event.start}|{event.kind}|{event.weeks}"
    return hashlib.sha1(seed.encode()).hexdigest()[:20] + "@summon"


def _title(event: Event) -> str:
    return f"Due: {event.title.strip()}" if event.kind == "deadline" else event.title.strip()


def _weekly_rule(dates: list[date], tz: ZoneInfo, start: time | None, all_day: bool):
    """RRULE + EXDATE values describing `dates` (all on the same weekday)."""
    first, last = dates[0], dates[-1]
    wanted = set(dates)
    gaps = []
    current = first
    while current <= last:
        if current not in wanted:
            gaps.append(current)
        current += timedelta(weeks=1)
    if all_day:
        until = last
        exdates = gaps
    else:
        # UNTIL must be in UTC when DTSTART has a TZID (RFC 5545 3.3.10).
        until = datetime.combine(last, start, tz).astimezone(timezone.utc)
        exdates = [datetime.combine(d, start, tz) for d in gaps]
    return {"FREQ": "WEEKLY", "UNTIL": until}, exdates


def build_ics(events: list[Event], tz_name: str, week1: date | None) -> bytes:
    """Build the calendar file. Only included events without problems should be passed in."""
    tz = ZoneInfo(tz_name)
    cal = Calendar()
    cal.add("prodid", PRODID)
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", "Summon")
    cal.add("x-wr-timezone", tz_name)
    stamp = datetime.now(timezone.utc).replace(microsecond=0)

    for event in events:
        dates = occurrence_dates(event, week1)
        first = dates[0]
        ve = VEvent()
        ve.add("uid", _uid(event, first))
        ve.add("dtstamp", stamp)
        ve.add("summary", _title(event))
        if event.location.strip():
            ve.add("location", event.location.strip())
        if event.notes.strip():
            ve.add("description", event.notes.strip())

        if event.all_day:
            ve.add("dtstart", first)
            ve.add("dtend", first + timedelta(days=1))  # DTEND is exclusive for dates
            ve.add("transp", "TRANSPARENT" if event.kind == "deadline" else "OPAQUE")
        else:
            ve.add("dtstart", datetime.combine(first, event.start, tz))
            finish = end_time(event)
            if finish is not None:
                ve.add("dtend", datetime.combine(first, finish, tz))
            else:
                ve.add("dtend", datetime.combine(first, event.start, tz))  # deadline: a point in time
                ve.add("transp", "TRANSPARENT")

        if len(dates) > 1:
            rule, exdates = _weekly_rule(dates, tz, event.start, event.all_day)
            ve.add("rrule", rule)
            for ex in exdates:
                ve.add("exdate", ex)

        if event.reminder is not None:
            alarm = Alarm()
            alarm.add("action", "DISPLAY")
            alarm.add("description", _title(event))
            alarm.add("trigger", timedelta(minutes=-event.reminder))
            ve.add_component(alarm)

        cal.add_component(ve)

    cal.add_missing_timezones()
    return cal.to_ical()


def google_link(event: Event, tz_name: str, week1: date | None) -> str | None:
    """'Add to Google Calendar' link, or None when a link can't represent the event exactly
    (teaching weeks with gaps need EXDATE, which Google's link format doesn't support)."""
    dates = occurrence_dates(event, week1)
    first = dates[0]
    if len(dates) > 1:
        expected = [first + timedelta(weeks=i) for i in range(len(dates))]
        if dates != expected:
            return None
    if event.all_day:
        span = f"{first:%Y%m%d}/{first + timedelta(days=1):%Y%m%d}"
    else:
        start = datetime.combine(first, event.start)
        finish = end_time(event)
        stop = datetime.combine(first, finish) if finish is not None else start
        span = f"{start:%Y%m%dT%H%M%S}/{stop:%Y%m%dT%H%M%S}"
    params = {"action": "TEMPLATE", "text": _title(event), "dates": span}
    if not event.all_day:
        params["ctz"] = tz_name
    if event.location.strip():
        params["location"] = event.location.strip()
    if event.notes.strip():
        params["details"] = event.notes.strip()
    if len(dates) > 1:
        params["recur"] = f"RRULE:FREQ=WEEKLY;COUNT={len(dates)}"
    return "https://calendar.google.com/calendar/render?" + urlencode(params)
