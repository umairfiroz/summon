from datetime import date, datetime, time, timedelta
from urllib.parse import parse_qs, urlparse

import recurring_ical_events
from icalendar import Calendar

from summon.calendar_export import build_ics, google_link
from summon.events import Event

TZ = "Europe/London"
WEEK1 = date(2026, 9, 28)


def expand(events, week1=WEEK1):
    cal = Calendar.from_ical(build_ics(events, TZ, week1))
    return cal, sorted(recurring_ical_events.of(cal).between(date(2026, 1, 1), date(2027, 12, 31)),
                       key=lambda c: str(c["DTSTART"].dt))


def test_teaching_weeks_keep_local_time_across_dst_and_skip_gaps():
    ev = Event(1, "Lecture", repeat="teaching_weeks", weekday=0, weeks="1-10, 12", start=time(9), end=time(11))
    cal, occ = expand([ev])
    starts = [o["DTSTART"].dt for o in occ]
    assert len(starts) == 11
    assert all(s.hour == 9 and s.minute == 0 for s in starts)            # 09:00 local, before and after 25 Oct
    assert {s.utcoffset() for s in starts} == {timedelta(hours=1), timedelta(0)}
    assert date(2026, 12, 7) not in [s.date() for s in starts]            # week 11 skipped
    assert starts[-1].date() == date(2026, 12, 14)
    assert len(cal.walk("VTIMEZONE")) == 1


def test_all_day_and_deadline_and_alarm():
    party = Event(1, "Social", date=date(2026, 10, 31), all_day=True)
    due = Event(2, "Report", kind="deadline", date=date(2026, 11, 13), start=time(16), reminder=1440)
    cal, occ = expand([party, due])
    vevents = {str(v["SUMMARY"]): v for v in cal.walk("VEVENT")}
    assert vevents["Social"]["DTSTART"].dt == date(2026, 10, 31)
    assert vevents["Social"]["DTEND"].dt == date(2026, 11, 1)             # exclusive end
    report = vevents["Due: Report"]
    assert report["DTSTART"].dt == report["DTEND"].dt
    assert str(report["TRANSP"]) == "TRANSPARENT"
    alarm = report.walk("VALARM")[0]
    assert alarm["TRIGGER"].dt == timedelta(days=-1)


def test_weekly_until_and_text_escaping():
    ev = Event(1, "Drop-in; help, Q&A", date=date(2026, 11, 3), repeat="weekly", until=date(2026, 11, 24),
               start=time(15), end=time(16), location="Building 59, Lab 2", notes="Bring laptop\nand charger")
    cal, occ = expand([ev])
    assert [o["DTSTART"].dt.date() for o in occ] == [date(2026, 11, 3), date(2026, 11, 10), date(2026, 11, 17), date(2026, 11, 24)]
    v = cal.walk("VEVENT")[0]
    assert str(v["SUMMARY"]) == "Drop-in; help, Q&A" and str(v["LOCATION"]) == "Building 59, Lab 2"


def test_uids_unique_and_stable():
    a = Event(1, "A", date=date(2026, 1, 1), all_day=True)
    b = Event(2, "B", date=date(2026, 1, 1), all_day=True)
    first = Calendar.from_ical(build_ics([a, b], TZ, None)).walk("VEVENT")
    second = Calendar.from_ical(build_ics([a, b], TZ, None)).walk("VEVENT")
    assert len({str(v["UID"]) for v in first}) == 2
    assert [str(v["UID"]) for v in first] == [str(v["UID"]) for v in second]


def test_google_links():
    timed = Event(1, "Badminton", date=date(2026, 10, 25), start=time(14), end=time(16), location="Jubilee")
    q = parse_qs(urlparse(google_link(timed, TZ, None)).query)
    assert q["dates"] == ["20261025T140000/20261025T160000"] and q["ctz"] == [TZ] and q["location"] == ["Jubilee"]
    weekly = Event(2, "Lab", repeat="teaching_weeks", weekday=1, weeks="2-11", start=time(14), end=time(16))
    assert parse_qs(urlparse(google_link(weekly, TZ, WEEK1)).query)["recur"] == ["RRULE:FREQ=WEEKLY;COUNT=10"]
    gaps = Event(3, "Tut", repeat="teaching_weeks", weekday=2, weeks="1-5, 7-11", start=time(10))
    assert google_link(gaps, TZ, WEEK1) is None
    allday = Event(4, "Social", date=date(2026, 10, 31), all_day=True)
    assert parse_qs(urlparse(google_link(allday, TZ, None)).query)["dates"] == ["20261031/20261101"]


def test_agent_skill_script_matches_app(tmp_path):
    import importlib.util
    import json
    import re
    from pathlib import Path

    script = Path(__file__).resolve().parents[1] / "skills/summon/scripts/make_ics.py"
    spec_ = importlib.util.spec_from_file_location("make_ics", script)
    mod = importlib.util.module_from_spec(spec_)
    import sys
    sys.modules["make_ics"] = mod
    spec_.loader.exec_module(mod)
    spec = {"timezone": TZ, "week1": "2026-09-28", "events": [
        {"title": "Lecture", "repeat": "teaching_weeks", "weekday": "Monday", "weeks": "1-10, 12", "start": "09:00", "end": "11:00"},
        {"title": "Report", "kind": "deadline", "date": "2026-11-13", "start": "16:00", "reminder_minutes": 1440}]}
    (tmp_path / "e.json").write_text(json.dumps(spec))
    assert mod.main(["x", str(tmp_path / "e.json"), str(tmp_path / "o.ics")]) == 0
    app_events = [Event(1, "Lecture", repeat="teaching_weeks", weekday=0, weeks="1-10, 12", start=time(9), end=time(11)),
                  Event(2, "Report", kind="deadline", date=date(2026, 11, 13), start=time(16), reminder=1440)]
    strip = lambda b: re.sub(rb"DTSTAMP:\S+", b"", b)
    assert strip((tmp_path / "o.ics").read_bytes()) == strip(build_ics(app_events, TZ, WEEK1))
