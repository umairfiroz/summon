"""Summon - turn screenshots, timetables, posters and PDFs into calendar events.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from summon import calendar_export, gemma, sample, theme, ui
from summon.events import KINDS, REPEATS, WEEKDAYS, Event, describe_when, occurrence_dates, problems

APP_DIR = Path(__file__).parent
ASSETS = APP_DIR / "assets"
MAX_FILES = 5
STEP_INDEX = {"add": 0, "review": 1, "export": 2}
FAIL_TEXT = "We couldn't find events in this file. Try a clearer image, or add the events manually."
TIMEZONES = ["Europe/London", "Europe/Dublin", "Europe/Paris", "Europe/Berlin", "Asia/Riyadh", "Asia/Dubai",
             "Asia/Karachi", "Asia/Kolkata", "Asia/Singapore", "America/New_York", "America/Chicago",
             "America/Los_Angeles", "Australia/Sydney", "UTC"]
REMINDERS = {0: "No reminder", 10: "10 minutes before", 30: "30 minutes before", 60: "1 hour before",
             1440: "1 day before", 2880: "2 days before", 10080: "1 week before"}

st.set_page_config(page_title="Summon", page_icon=":material/event_available:", layout="wide")
ss = st.session_state


# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #

def init_state() -> None:
    defaults = {
        "step": "add", "source": None, "sample_key": None, "sources": [], "raw": None,
        "events": [], "week1": None, "tz": "Europe/London", "extract_error": None,
        "flash": None, "next_id": 1,
    }
    for key, value in defaults.items():
        if key not in ss:
            ss[key] = value


def new_id() -> int:
    ss.next_id += 1
    return ss.next_id


def today() -> date:
    return datetime.now(ZoneInfo(ss.tz)).date()


def api_key() -> str | None:
    try:
        key = st.secrets.get("GEMINI_API_KEY")
    except Exception:  # no secrets file locally
        key = None
    return key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ss.get("user_api_key") or None


def event_by_id(eid: int) -> Event:
    return next(ev for ev in ss.events if ev.id == eid)


def make_event(fields: dict) -> Event:
    ev = Event(id=new_id(), **{k: v for k, v in fields.items() if k in Event.__dataclass_fields__ and k != "id"})
    if ev.kind == "deadline" and ev.reminder is None:
        ev.reminder = 1440
    return ev


def set_events(field_dicts: list[dict]) -> None:
    ss.events = [make_event(f) for f in field_dicts]


def reset() -> None:
    for key in ("source", "sample_key", "raw", "extract_error", "flash", "week1"):
        ss[key] = None
    ss.sources, ss.events = [], []


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #

def load_sample(key: str) -> None:
    reset()
    spec = sample.SAMPLES[key]
    path = ASSETS / spec["file"]
    data = path.read_bytes()
    preview = gemma.pdf_preview(data) if path.suffix == ".pdf" else data
    ss.source, ss.sample_key = "sample", key
    ss.sources = [{"name": spec["label"], "data": data, "preview": preview, "pdf": path.suffix == ".pdf"}]
    set_events([sample.to_event_fields(raw) for raw in spec["events"]])
    ss.week1 = spec.get("week1")
    ss.step = "review"


def start_manual() -> None:
    reset()
    ss.source = "manual"
    ss.events = [Event(id=new_id(), date=today())]
    ss.step = "review"


def find_events(files: list[dict]) -> None:
    """files: [{"name", "data", "pdf"}]. Sends everything to Gemma in one request."""
    ss.extract_error = None
    parts, previews = [], []
    try:
        with st.spinner("Finding events…"):
            for f in files:
                if f["pdf"]:
                    pdf_parts, _ = gemma.pdf_to_parts(f["data"])
                    parts += pdf_parts
                    previews.append({**f, "preview": gemma.pdf_preview(f["data"])})
                else:
                    parts.append(gemma.image_part(f["data"]))
                    previews.append({**f, "preview": f["data"]})
            found, raw = gemma.extract_events(gemma.make_client(api_key()), parts, today(), ss.tz)
    except gemma.GemmaError as exc:
        ss.extract_error = str(exc)
        return
    keep_week1 = ss.week1
    reset()
    ss.source, ss.sources, ss.raw = "gemma", previews, raw
    ss.week1 = keep_week1
    set_events(found)
    if not found:
        ss.flash = ("warning", "Gemma didn't find any events in that file. You can add them manually below.")
    ss.step = "review"
    st.rerun()


# --------------------------------------------------------------------------- #
# Widget callbacks: keep the canonical events in sync with the widgets
# --------------------------------------------------------------------------- #

def cb_set(eid: int, field: str, key: str) -> None:
    setattr(event_by_id(eid), field, ss[key])


def cb_reminder(eid: int, key: str) -> None:
    event_by_id(eid).reminder = ss[key] or None


def cb_kind(eid: int, key: str) -> None:
    ev = event_by_id(eid)
    ev.kind = ss[key] or ev.kind
    if ev.kind == "deadline" and ev.reminder is None:
        ev.reminder = 1440


def cb_repeat(eid: int, key: str) -> None:
    ev = event_by_id(eid)
    ev.repeat = ss[key]
    if ev.repeat == "teaching_weeks" and ev.weekday is None and ev.date is not None:
        ev.weekday = ev.date.weekday()
    if ev.repeat in ("none", "weekly") and ev.date is None:
        ev.date = today()


def cb_remove(eid: int) -> None:
    title = event_by_id(eid).title or "Untitled event"
    ss.events = [ev for ev in ss.events if ev.id != eid]
    ss.flash = ("info", f"Removed “{title}”.")


def cb_add_event() -> None:
    ss.events.append(Event(id=new_id(), date=today()))


def cb_week1() -> None:
    ss.week1 = ss.week1_widget


def go(step: str) -> None:
    ss.step = step


def bind(key: str, value) -> str:
    """Set a widget's value from the canonical state before it is drawn."""
    ss[key] = value
    return key


# --------------------------------------------------------------------------- #
# Page shell
# --------------------------------------------------------------------------- #

init_state()

with st.container(key="header"):
    left, right = st.columns([3, 1], vertical_alignment="center")
    left.html(ui.brand())
    with right:
        mode = st.segmented_control(
            "Theme", theme.MODES, format_func=lambda m: theme.MODE_LABELS[m], default="system",
            required=True, key="theme", bind="query-params", help="System follows your device setting.",
        ) or "system"

st.html(theme.css(mode))
st.html(theme.persistence_script(mode), unsafe_allow_javascript=True)
st.html(ui.page_title())
st.html(ui.steps(STEP_INDEX[ss.step]))

if ss.flash:
    kind, text = ss.flash
    st.html(ui.notice(text, kind))
    ss.flash = None


def week1_value() -> date | None:
    return ss.week1


def ready_events() -> list[Event]:
    return [ev for ev in ss.events if ev.include and not problems(ev, week1_value())]


def source_panel() -> None:
    with st.container(key="panel_source"):
        label = {"sample": "Sample", "gemma": "Read by Gemma 4", "manual": "Entered manually"}[ss.source]
        names = ", ".join(s["name"] for s in ss.sources) or "Manual entry"
        st.html(ui.badge(label, neutral=ss.source != "gemma") + ui.source_name(names))
        for src in ss.sources:
            if src.get("preview"):
                with st.expander(f"Preview: {src['name']}" if len(ss.sources) > 1 else "Preview", expanded=True):
                    with st.container(key=f"preview_area_{abs(hash(src['name'])) % 10_000}"):
                        st.image(src["preview"], width="stretch")
                        if src["pdf"]:
                            st.caption("First page of the PDF.")
        if ss.source == "sample":
            st.caption("Sample data for the demo. These events were preloaded, not read by AI.")
            if api_key():
                if st.button("Read this sample with Gemma 4", width="stretch"):
                    find_events([{"name": s["name"], "data": s["data"], "pdf": s["pdf"]} for s in ss.sources])
                if ss.extract_error:
                    st.html(ui.notice(f"{FAIL_TEXT} Details: {ss.extract_error}", "error"))
        if ss.source == "gemma" and ss.raw is not None:
            with st.expander("What Gemma 4 extracted"):
                st.code(json.dumps(ss.raw, indent=2, ensure_ascii=False, default=str), language="json")
        st.button("Choose different files", width="stretch", on_click=go, args=("add",))


# ---------- 1. Add ---------------------------------------------------------- #
if ss.step == "add":
    with st.container(key="panel_add"):
        st.html(ui.heading("Start with a screenshot or PDF",
                           "Timetables, posters, group chats, emails and coursework briefs all work."))
        uploads = st.file_uploader("Choose files", type=["png", "jpg", "jpeg", "webp", "pdf"],
                                   accept_multiple_files=True, key="uploader",
                                   help=f"Up to {MAX_FILES} files. They're read together, so you can add a whole week of screenshots.")
        st.caption("Files are sent to Google's Gemini API, where the open-weight Gemma 4 model reads them. "
                   "Summon doesn't save your files; they're cleared when you close the page.")
        c_tz, c_today = st.columns([1, 1], vertical_alignment="bottom")
        ss.tz = c_tz.selectbox("Time zone", TIMEZONES, index=TIMEZONES.index(ss.tz),
                               help="Events are created in this time zone.")
        c_today.caption(f"Dates like “next Friday” are worked out from today, {today():%A} {today().day} {today():%B %Y}.")

        if not api_key():
            st.html(ui.notice("Add a Gemini API key to read your own files. The samples and manual entry work without one.", "info"))
            st.text_input("Gemini API key", type="password", key="user_api_key",
                          help="Free from aistudio.google.com. Kept only for this browser session.")

        too_many = uploads is not None and len(uploads) > MAX_FILES
        if too_many:
            st.html(ui.notice(f"Choose up to {MAX_FILES} files at a time. Remove {len(uploads) - MAX_FILES} to continue.", "error"))
        if st.button("Find events", type="primary", width="stretch",
                     disabled=not uploads or too_many or not api_key()):
            find_events([{"name": u.name, "data": u.getvalue(), "pdf": u.name.lower().endswith(".pdf")} for u in uploads])
        if ss.extract_error:
            st.html(ui.notice(f"{FAIL_TEXT} Details: {ss.extract_error}", "error"))
        if not uploads:
            st.caption("Choose at least one file to continue.")

        st.html(ui.subheading("Try a sample or add events yourself"))
        c1, c2, c3, c4 = st.columns(4)
        c1.button("Sample timetable", on_click=load_sample, args=("timetable",), width="stretch",
                  help="A university timetable with teaching weeks.")
        c2.button("Sample group chat", on_click=load_sample, args=("chat",), width="stretch",
                  help="Plans mentioned in a chat, with relative dates.")
        c3.button("Sample coursework brief", on_click=load_sample, args=("brief",), width="stretch",
                  help="A PDF with deadlines.")
        c4.button("Add events manually", on_click=start_manual, width="stretch")

# ---------- 2. Review ------------------------------------------------------- #
elif ss.step == "review":
    col_left, col_right = st.columns([38, 62], gap="medium")
    with col_left:
        source_panel()
    with col_right:
        with st.container(key="panel_review"):
            n = len(ss.events)
            st.html(ui.heading("Review events", "Check each event before adding it to your calendar."))
            if ss.source == "gemma" and n:
                st.html(ui.notice(f"Gemma found {n} event{'s' if n != 1 else ''}. Check the dates and times, "
                                  "especially anything marked “Gemma wasn't sure”.", "info"))

            if any(ev.repeat == "teaching_weeks" for ev in ss.events):
                st.html(ui.subheading("Teaching weeks"))
                ss.week1_widget = ss.week1
                st.date_input("Week 1 starts on (a Monday)", key="week1_widget", on_change=cb_week1,
                              format="DD/MM/YYYY", help="Check your university's term dates. Week numbers count from this Monday.")
                if ss.source == "sample" and ss.sample_key == "timetable":
                    st.caption("Sample value. Change it to match your university's term dates.")
                if ss.week1 is not None and ss.week1.weekday() != 0:
                    st.html(ui.notice(f"{ss.week1:%A} {ss.week1.day} {ss.week1:%B} isn't a Monday. Choose the Monday of week 1.", "error"))

            if not ss.events:
                st.html(ui.empty_events())

            week1 = week1_value()
            for ev in ss.events:
                eid = ev.id
                issues = problems(ev, week1)
                status = "Not included · " if not ev.include else ("Needs attention · " if issues else "")
                label = f"{status}{ev.title or 'Untitled event'} — {describe_when(ev, week1)}"
                with st.expander(label, expanded=bool(issues or ev.unclear) and ev.include):
                    if ev.unclear:
                        st.html(ui.notice(ev.unclear, "warning", "Gemma wasn't sure"))
                    c_inc, c_kind = st.columns([1, 1], vertical_alignment="center")
                    c_inc.checkbox("Add to calendar", key=bind(f"inc_{eid}", ev.include), on_change=cb_set,
                                   args=(eid, "include", f"inc_{eid}"))
                    c_kind.segmented_control("Type", list(KINDS), format_func=KINDS.get, required=True,
                                             key=bind(f"kind_{eid}", ev.kind), on_change=cb_kind, args=(eid, f"kind_{eid}"))
                    st.text_input("Title", key=bind(f"title_{eid}", ev.title), on_change=cb_set,
                                  args=(eid, "title", f"title_{eid}"), max_chars=120, placeholder="What is it?")

                    st.selectbox("Repeats", list(REPEATS), format_func=REPEATS.get, key=bind(f"rep_{eid}", ev.repeat),
                                 on_change=cb_repeat, args=(eid, f"rep_{eid}"))
                    if ev.repeat == "teaching_weeks":
                        c_day, c_weeks = st.columns(2)
                        c_day.selectbox("Day", list(range(7)), format_func=lambda i: WEEKDAYS[i],
                                        placeholder="Choose a day", key=bind(f"wd_{eid}", ev.weekday),
                                        on_change=cb_set, args=(eid, "weekday", f"wd_{eid}"))
                        c_weeks.text_input("Teaching weeks", key=bind(f"weeks_{eid}", ev.weeks), on_change=cb_set,
                                           args=(eid, "weeks", f"weeks_{eid}"), placeholder="1-10, 12",
                                           help="Week numbers as they appear on the timetable, e.g. 1-10, 12.")
                    else:
                        c_date, c_until = st.columns(2)
                        c_date.date_input("Date" if ev.repeat == "none" else "First date", key=bind(f"date_{eid}", ev.date),
                                          format="DD/MM/YYYY", on_change=cb_set, args=(eid, "date", f"date_{eid}"))
                        if ev.repeat == "weekly":
                            c_until.date_input("Repeat until", key=bind(f"until_{eid}", ev.until),
                                               format="DD/MM/YYYY", on_change=cb_set, args=(eid, "until", f"until_{eid}"))

                    st.checkbox("All day", key=bind(f"allday_{eid}", ev.all_day), on_change=cb_set,
                                args=(eid, "all_day", f"allday_{eid}"))
                    if not ev.all_day:
                        c_start, c_end = st.columns(2)
                        c_start.time_input("Due time" if ev.kind == "deadline" else "Start", key=bind(f"start_{eid}", ev.start),
                                           step=300, on_change=cb_set, args=(eid, "start", f"start_{eid}"))
                        if ev.kind == "event":
                            c_end.time_input("End", key=bind(f"end_{eid}", ev.end), step=300,
                                             on_change=cb_set, args=(eid, "end", f"end_{eid}"),
                                             help="Leave empty to make it one hour long.")
                    c_loc, c_rem = st.columns(2)
                    c_loc.text_input("Location", key=bind(f"loc_{eid}", ev.location), on_change=cb_set,
                                     args=(eid, "location", f"loc_{eid}"), max_chars=120)
                    c_rem.selectbox("Reminder", list(REMINDERS), format_func=REMINDERS.get,
                                    key=bind(f"rem_{eid}", ev.reminder or 0), on_change=cb_reminder, args=(eid, f"rem_{eid}"))
                    st.text_input("Notes", key=bind(f"notes_{eid}", ev.notes), on_change=cb_set,
                                  args=(eid, "notes", f"notes_{eid}"), max_chars=300)
                    if issues and ev.include:
                        st.html(ui.notice(" ".join(issues), "warning", "To add this event"))
                    st.button("Remove event", key=f"remove_{eid}", on_click=cb_remove, args=(eid,))

            st.button("Add an event", icon=":material/add:", type="tertiary", on_click=cb_add_event)

            included = [ev for ev in ss.events if ev.include]
            blocked = [ev.title or "Untitled event" for ev in included if problems(ev, week1)]
            if not included:
                st.html(ui.notice("Choose at least one event to add to your calendar.", "warning", "Before you continue"))
            elif blocked:
                st.html(ui.notice(f"Fix or untick: {', '.join(blocked)}.", "warning", "Before you continue"))
            else:
                st.html(ui.notice(f"{len(included)} event{'s' if len(included) != 1 else ''} ready to add.", "success", "Ready"))
            st.button("Continue to export", type="primary", width="stretch", disabled=not included or bool(blocked),
                      on_click=go, args=("export",))

# ---------- 3. Export ------------------------------------------------------- #
elif ss.step == "export":
    week1 = week1_value()
    events = ready_events()
    col_left, col_right = st.columns([38, 62], gap="medium")
    with col_left:
        source_panel()
    with col_right:
        with st.container(key="panel_export"):
            if not events:
                st.html(ui.notice("There are no events ready to export.", "warning"))
                st.button("Back to review", on_click=go, args=("review",))
                st.stop()
            entries = sum(len(occurrence_dates(ev, week1)) for ev in events)
            st.html(ui.heading("Your calendar file is ready",
                               f"{len(events)} event{'s' if len(events) != 1 else ''}, {entries} calendar "
                               f"entr{'ies' if entries != 1 else 'y'}, in {ss.tz} time."))
            rows = [(("Due: " if ev.kind == "deadline" else "") + ev.title, describe_when(ev, week1), ev.location) for ev in events]
            st.html(ui.event_list(rows, "Events in the calendar file"))

            ics = calendar_export.build_ics(events, ss.tz, week1)
            st.download_button("Download calendar file (.ics)", data=ics, file_name="summon-events.ics",
                               mime="text/calendar", type="primary", width="stretch", icon=":material/download:")
            with st.expander("How to add the file to your calendar"):
                st.markdown(
                    "- **Google Calendar (computer):** Settings → Import & export → Import, choose the file, then Import.\n"
                    "- **Apple Calendar (Mac or iPhone):** open the file and choose Add.\n"
                    "- **Outlook:** Add calendar → Upload from file, choose the file, then Import.\n"
                    "- **Android:** import it at calendar.google.com on a computer, or use the links below one at a time.\n\n"
                    "Importing the same file twice can create duplicates, so import it once."
                )

            st.html(ui.subheading("Or add them to Google Calendar one at a time"))
            for ev in events:
                link = calendar_export.google_link(ev, ss.tz, week1)
                label = ("Due: " if ev.kind == "deadline" else "") + (ev.title or "Untitled event")
                if link:
                    st.link_button(f"Add “{label}”", link, icon=":material/open_in_new:", width="stretch")
                else:
                    st.caption(f"“{label}” skips some weeks, which Google's add link can't do. Use the calendar file for this one.")

            c1, c2 = st.columns(2)
            c1.button("Back to review", on_click=go, args=("review",), width="stretch")
            if c2.button("Start again", width="stretch"):
                reset()
                ss.step = "add"
                st.rerun()
