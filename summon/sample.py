"""Labelled demo samples. Each has an image or PDF in assets/ and the events it contains,
preloaded so the demo works without an API key. The app always marks these as samples."""

from datetime import date, time

SAMPLES = {
    "timetable": {
        "label": "Sample timetable",
        "file": "sample_timetable.png",
        "week1": date(2026, 9, 28),
        "events": [
            {"title": "Software Engineering lecture", "weekday": 0, "start": time(9), "end": time(11),
             "location": "Building 32 / Room 1015", "weeks": "1-10, 12"},
            {"title": "Algorithms lab", "weekday": 1, "start": time(14), "end": time(16),
             "location": "Building 59 / Lab 2", "weeks": "2-11"},
            {"title": "Computer Networks tutorial", "weekday": 2, "start": time(10), "end": time(11),
             "location": "Building 2A / Room 1077", "weeks": "1-5, 7-11"},
            {"title": "Mathematics for CS lecture", "weekday": 3, "start": time(13), "end": time(15),
             "location": "Building 35 / Room 1001", "weeks": "1-12"},
            {"title": "Personal tutor meeting", "weekday": 4, "start": time(11), "end": time(12),
             "location": "Building 53 / Room 4025", "weeks": "1, 4, 8"},
        ],
    },
    "chat": {
        "label": "Sample group chat",
        "file": "sample_chat.png",
        "events": [
            {"title": "Badminton", "date": date(2026, 10, 25), "start": time(14), "end": time(16),
             "location": "Jubilee Sports Centre"},
            {"title": "ECSS Halloween social", "date": date(2026, 10, 30), "start": time(19, 30),
             "location": "The Stag's", "unclear": "No end time given."},
            {"title": "Algorithms quiz closes", "kind": "deadline", "date": date(2026, 10, 29), "start": time(23, 59)},
        ],
    },
    "brief": {
        "label": "Sample coursework brief",
        "file": "sample_coursework_brief.pdf",
        "events": [
            {"title": "Design report (Part A)", "kind": "deadline", "date": date(2026, 11, 13), "start": time(16),
             "location": "Online submission", "notes": "PDF, max 3,000 words. 50% of the coursework."},
            {"title": "Peer assessment form (Part B)", "kind": "deadline", "date": date(2026, 11, 20), "start": time(23, 59),
             "location": "Online submission"},
            {"title": "Team demonstration (Part C)", "date": date(2026, 12, 2), "start": time(10), "end": time(12),
             "location": "Building 32, Room 1015", "notes": "15-minute team demo."},
            {"title": "Coursework drop-in help", "date": date(2026, 11, 3), "start": time(15), "end": time(16),
             "location": "Building 59, Lab 2", "until": date(2026, 11, 24)},
        ],
    },
}


def to_event_fields(raw: dict) -> dict:
    """Fill in defaults so a sample entry matches gemma.parse_events() output."""
    fields = {"title": "", "kind": "event", "date": None, "start": None, "end": None, "all_day": False,
              "location": "", "notes": "", "repeat": "none", "until": None, "weekday": None, "weeks": "",
              "unclear": None}
    fields.update(raw)
    if fields["weeks"]:
        fields["repeat"] = "teaching_weeks"
    elif fields["until"]:
        fields["repeat"] = "weekly"
    return fields
