from datetime import date, time

import pytest

from summon.events import Event, describe_when, end_time, format_weeks, occurrence_dates, parse_weeks, problems

WEEK1 = date(2026, 9, 28)  # a Monday


@pytest.mark.parametrize("text,expected", [
    ("1-10, 12", list(range(1, 11)) + [12]),
    ("Weeks 1-5, 7-11", [1, 2, 3, 4, 5, 7, 8, 9, 10, 11]),
    ("1, 4, 8", [1, 4, 8]),
    ("2–4", [2, 3, 4]),
    ("1 to 3; 5", [1, 2, 3, 5]),
    ("3,3,1-2", [1, 2, 3]),
])
def test_parse_weeks(text, expected):
    assert parse_weeks(text) == expected


@pytest.mark.parametrize("text", ["", "10-1", "abc", "0-3", "1-99"])
def test_parse_weeks_rejects(text):
    with pytest.raises(ValueError):
        parse_weeks(text)


def test_format_weeks_round_trip():
    assert format_weeks([1, 2, 3, 5, 7, 8]) == "1-3, 5, 7-8"
    assert parse_weeks(format_weeks([1, 2, 3, 5, 7, 8])) == [1, 2, 3, 5, 7, 8]


def test_teaching_week_dates():
    ev = Event(1, "Lab", repeat="teaching_weeks", weekday=1, weeks="2-3, 12", start=time(14))
    assert occurrence_dates(ev, WEEK1) == [date(2026, 10, 6), date(2026, 10, 13), date(2026, 12, 15)]


def test_teaching_weeks_need_a_monday():
    ev = Event(1, "Lab", repeat="teaching_weeks", weekday=1, weeks="1", start=time(14))
    assert "Set the date week 1 starts on." in problems(ev, None)
    assert "Week 1 must start on a Monday." in problems(ev, date(2026, 9, 29))


def test_weekly_until():
    ev = Event(1, "Drop-in", date=date(2026, 11, 3), repeat="weekly", until=date(2026, 11, 24), start=time(15))
    assert occurrence_dates(ev, None) == [date(2026, 11, 3), date(2026, 11, 10), date(2026, 11, 17), date(2026, 11, 24)]
    ev.until = date(2026, 11, 1)
    assert "The repeat must end on or after the first date." in problems(ev, None)


def test_problems():
    assert problems(Event(1, "", date=date(2026, 1, 1), all_day=True), None) == ["Add a title."]
    assert "Add a date." in problems(Event(1, "X", start=time(9)), None)
    assert "Add a start time, or mark it as all day." in problems(Event(1, "X", date=date(2026, 1, 1)), None)
    assert "The end time must be after the start time." in problems(Event(1, "X", date=date(2026, 1, 1), start=time(10), end=time(9)), None)
    assert problems(Event(1, "X", date=date(2026, 1, 1), start=time(10)), None) == []


def test_default_end_and_deadlines():
    assert end_time(Event(1, "X", date=date(2026, 1, 1), start=time(19, 30))) == time(20, 30)
    assert end_time(Event(1, "X", date=date(2026, 1, 1), start=time(23, 30))) == time(23, 59)
    assert end_time(Event(1, "X", kind="deadline", date=date(2026, 1, 1), start=time(16))) is None


def test_describe_when():
    ev = Event(1, "L", repeat="teaching_weeks", weekday=0, weeks="1-10, 12", start=time(9), end=time(11))
    assert describe_when(ev, WEEK1) == "Mon 09:00–11:00 · weeks 1-10, 12 (11 times)"
    assert describe_when(Event(1, "D", kind="deadline", date=date(2026, 11, 13), start=time(16)), None) == "Fri 13 Nov 2026 · due 16:00"
