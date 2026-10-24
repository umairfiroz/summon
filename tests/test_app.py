"""End-to-end UI tests: the real Streamlit app, with Gemma faked out where needed."""

import html
from datetime import date, time
from pathlib import Path

import pytest
import recurring_ical_events
from icalendar import Calendar
from streamlit.testing.v1 import AppTest

from summon import calendar_export, gemma

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def text(at) -> str:
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption] + [e.label for e in at.expander]
    parts += [str(getattr(el, "proto", "")) for el in at.get("html")]
    return html.unescape(" ".join(parts))


def button(at, label):
    return next(b for b in at.button if b.label == label)


def keys(widgets, prefix):
    return [w.key for w in widgets if w.key and str(w.key).startswith(prefix)]


@pytest.fixture
def app(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    return at


def export_ics(at) -> Calendar:
    """Go to export and rebuild the same file the download button serves."""
    button(at, "Continue to export").click().run()
    assert not at.exception and "Your calendar file is ready" in text(at)
    ss = at.session_state
    from summon.events import problems
    events = [ev for ev in ss["events"] if ev.include and not problems(ev, ss["week1"])]
    return Calendar.from_ical(calendar_export.build_ics(events, ss["tz"], ss["week1"]))


def test_add_screen(app):
    t = text(app)
    assert "Start with a screenshot or PDF" in t and "Add a Gemini API key" in t
    assert button(app, "Find events").disabled


def test_timetable_sample_to_export(app):
    button(app, "Sample timetable").click().run()
    t = text(app)
    assert app.date_input(key="week1_widget").value == date(2026, 9, 28)
    assert "Sample value" in t and "5 events ready to add." in t
    cal = export_ics(app)
    occ = recurring_ical_events.of(cal).between(date(2026, 9, 1), date(2027, 1, 31))
    assert len(occ) == 11 + 10 + 10 + 12 + 3
    assert "46 calendar entries" in text(app)
    assert "skips some weeks" in text(app)  # honest about Google link limits


def test_week1_must_be_monday(app):
    button(app, "Sample timetable").click().run()
    app.date_input(key="week1_widget").set_value(date(2026, 9, 29)).run()
    t = text(app)
    assert "isn't a Monday" in t and button(app, "Continue to export").disabled


def test_chat_and_brief_samples_export(app):
    button(app, "Sample group chat").click().run()
    assert "Gemma wasn't sure" in text(app)
    cal = export_ics(app)
    assert {str(v["SUMMARY"]) for v in cal.walk("VEVENT")} == {"Badminton", "ECSS Halloween social", "Due: Algorithms quiz closes"}

    at = AppTest.from_file(APP, default_timeout=30).run()
    button(at, "Sample coursework brief").click().run()
    cal = export_ics(at)
    occ = recurring_ical_events.of(cal).between(date(2026, 10, 1), date(2027, 1, 31))
    assert len(occ) == 3 + 4  # two deadlines + demo + four weekly drop-ins
    alarms = [v for v in cal.walk("VEVENT") if v.walk("VALARM")]
    assert len(alarms) == 2  # deadlines get a 1-day reminder by default


def test_manual_entry_validation_and_edit(app):
    button(app, "Add events manually").click().run()
    assert "Needs attention" in text(app) and button(app, "Continue to export").disabled
    app.text_input(key=keys(app.text_input, "title_")[0]).input("Dentist").run()
    app.time_input(key=keys(app.time_input, "start_")[0]).set_value(time(10, 30)).run()
    assert not button(app, "Continue to export").disabled
    app.time_input(key=keys(app.time_input, "end_")[0]).set_value(time(10, 0)).run()
    assert "The end time must be after the start time." in text(app)


def test_untick_and_remove(app):
    button(app, "Sample group chat").click().run()
    app.checkbox(key=keys(app.checkbox, "inc_")[0]).uncheck().run()
    assert "Not included · Badminton" in text(app) and "2 events ready to add." in text(app)
    button(app, "Remove event").click().run()
    assert "Removed" in text(app)


def test_theme_switch_keeps_edits(app):
    button(app, "Sample group chat").click().run()
    key = keys(app.text_input, "title_")[0]
    app.text_input(key=key).input("Badminton doubles").run()
    for mode in ("dark", "light", "system"):
        next(g for g in app.button_group if g.label == "Theme").set_value(mode).run()
        assert not app.exception
        assert app.text_input(key=key).value == "Badminton doubles"


def test_extraction_failure_message(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setattr(gemma, "make_client", lambda key=None: object())

    def fail(*a, **k):
        raise gemma.GemmaError("Couldn't reach the Gemini API. Check your internet connection.")

    monkeypatch.setattr(gemma, "extract_events", fail)
    at = AppTest.from_file(APP, default_timeout=30).run()
    button(at, "Sample group chat").click().run()
    button(at, "Read this sample with Gemma 4").click().run()
    t = text(at)
    assert "We couldn't find events in this file." in t and "internet connection" in t


def test_live_extraction_path(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setattr(gemma, "make_client", lambda key=None: object())
    monkeypatch.setattr(gemma, "extract_events", lambda client, parts, today, tz, model=None: (
        gemma.parse_events({"events": [{"title": "Quiz", "kind": "deadline", "date": "2026-10-29", "start": "23:59"}]}),
        {"events": []}))
    at = AppTest.from_file(APP, default_timeout=30).run()
    button(at, "Sample coursework brief").click().run()
    button(at, "Read this sample with Gemma 4").click().run()
    t = text(at)
    assert "Read by Gemma 4" in t and "Gemma found 1 event" in t and "What Gemma 4 extracted" in t
