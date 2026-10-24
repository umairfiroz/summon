import io
from datetime import date, time
from pathlib import Path
from types import SimpleNamespace

import pytest

from summon import gemma

ASSETS = Path(__file__).resolve().parents[1] / "assets"


def test_extract_json_variants():
    assert gemma.extract_json('{"a": 1}') == {"a": 1}
    assert gemma.extract_json('```json\n{"events": []}\n```') == {"events": []}
    assert gemma.extract_json('Here you go: {"events": [1]} thanks') == {"events": [1]}
    with pytest.raises(ValueError):
        gemma.extract_json("no json")


def test_parse_events_shapes():
    out = gemma.parse_events({"events": [
        {"title": "Lecture", "weekday": "Monday", "weeks": "1-10", "start": "09:00", "end": "11:00"},
        {"title": "CW1", "kind": "deadline", "date": "2026-11-13", "start": "16.00"},
        {"title": "Social", "date": "2026-10-31"},
        {"title": "Drop-in", "date": "2026-11-03", "start": "15:00", "repeat_weekly_until": "2026-11-24"},
        {"title": "Bad", "date": "31/10", "start": "25:00", "unclear": "blurry"},
        {"title": "", "date": None},
        "junk",
    ]})
    assert [e["title"] for e in out] == ["Lecture", "CW1", "Social", "Drop-in", "Bad"]
    lec, cw, social, dropin, bad = out
    assert lec["repeat"] == "teaching_weeks" and lec["weekday"] == 0 and not lec["all_day"]
    assert cw["kind"] == "deadline" and cw["start"] == time(16)
    assert social["all_day"] is True and social["date"] == date(2026, 10, 31)
    assert dropin["repeat"] == "weekly" and dropin["until"] == date(2026, 11, 24)
    assert bad["date"] is None and bad["start"] is None
    assert "blurry" in bad["unclear"] and "31/10" in bad["unclear"] and "25:00" in bad["unclear"]


def test_parse_events_rejects_wrong_shape():
    with pytest.raises(gemma.GemmaError):
        gemma.parse_events({"nope": 1})
    assert gemma.parse_events([]) == []


class FakeModels:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def generate_content(self, model, contents):
        self.calls.append(contents)
        return SimpleNamespace(text=self.replies.pop(0))


def test_extract_events_retries_and_includes_today():
    models = FakeModels(["not json", '{"events": [{"title": "Badminton", "date": "2026-10-25", "start": "14:00"}]}'])
    events, raw = gemma.extract_events(SimpleNamespace(models=models), ["text"], date(2026, 10, 24), "Europe/London")
    assert events[0]["title"] == "Badminton" and len(models.calls) == 2
    assert "Saturday 24 October 2026" in models.calls[0][-1] and "2026-10-24" in models.calls[0][-1]


def test_network_failure_is_friendly():
    class Boom:
        def generate_content(self, model, contents):
            raise ConnectionError("down")

    with pytest.raises(gemma.GemmaError, match="internet"):
        gemma._generate(SimpleNamespace(models=Boom()), "m", "x")


def test_text_pdf_is_sent_as_text():
    parts, desc = gemma.pdf_to_parts((ASSETS / "sample_coursework_brief.pdf").read_bytes())
    assert desc.startswith("Text from 1 page")
    assert "16:00, Friday 13 November 2026" in parts[0]


def test_scanned_pdf_is_sent_as_images():
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (600, 800), "white").save(buf, format="PDF")
    parts, desc = gemma.pdf_to_parts(buf.getvalue())
    assert "scanned" in desc and len(parts) == 1


def test_bad_pdf_and_bad_image():
    with pytest.raises(gemma.GemmaError):
        gemma.pdf_to_parts(b"not a pdf")
    with pytest.raises(gemma.GemmaError):
        gemma.prepare_image(b"not an image")
