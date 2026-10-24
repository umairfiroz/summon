"""End-to-end UI tests: run the real Streamlit app with Gemma faked out."""

import html
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from split_and_spell import gemma

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def page_text(at) -> str:
    """All rendered text: markdown, st.html blocks, captions."""
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption]
    parts += [str(getattr(el, "proto", "")) for el in at.get("html")]
    return html.unescape(" ".join(parts))


def keys(widgets, prefix):
    return [w.key for w in widgets if w.key and str(w.key).startswith(prefix)]


def button(at, label):
    return next(b for b in at.button if b.label == label)


def group(at, label):
    return next(g for g in at.button_group if g.label == label)


@pytest.fixture
def app(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    return at


def start_sample(at):
    button(at, "Use sample receipt").click().run()
    assert not at.exception, at.exception
    return at


def test_upload_screen_without_key(app):
    text = page_text(app)
    assert "Start with your receipt" in text
    assert "Add a Gemini API key" in text
    assert button(app, "Read receipt").disabled


def test_sample_review_reconciles(app):
    at = start_sample(app)
    text = page_text(at)
    assert "Sample receipt" in text and "The Lantern Kitchen" in text
    assert "£56.00" in text and "Matches" in text
    assert not button(at, "Continue to split").disabled


def test_sample_equal_custom_and_by_item(app):
    at = start_sample(app)
    button(at, "Continue to split").click().run()
    text = page_text(at)
    assert "£14.00 each" in text and "£56.00 split between 4 people" in text
    assert "Total assigned" in text

    group(at, "Split method").set_value("Custom amounts").run()
    text = page_text(at)
    assert "All £56.00 assigned" in text
    assert not button(at, "Confirm split").disabled
    # Under-assign: £8.00 left and confirmation blocked with an explanation.
    at.number_input(key=keys(at.number_input, "custom_")[-1]).set_value(2.0).run()
    text = page_text(at)
    assert "£8.00 left to assign" in text and "Assign the remaining £8.00 to continue." in text
    assert button(at, "Confirm split").disabled

    group(at, "Split method").set_value("By item").run()
    text = page_text(at)
    for amount in ("£17.00", "£19.00", "£12.00", "£8.00"):
        assert amount in text
    assert "½ Garlic bread" in text
    button(at, "Confirm split").click().run()
    text = page_text(at)
    assert "Your split is ready" in text and "Total assigned" in text and "£56.00" in text
    assert "Paid" not in text and "Settled" not in text


def test_theme_switch_keeps_edits(app):
    at = start_sample(app)
    first_item = keys(at.number_input, "item_price_")[0]
    at.number_input(key=first_item).set_value(15.0).run()
    for mode in ("dark", "light", "system"):
        group(at, "Theme").set_value(mode).run()
        assert not at.exception
        assert at.number_input(key=first_item).value == 15.0
        assert "but the receipt total is £56.00" in page_text(at)


def test_mismatch_requires_confirmation(app):
    at = start_sample(app)
    remove = next(b for b in at.button if b.label == "Remove")
    remove.click().run()  # drop Pumpkin pasta (£14.00)
    text = page_text(at)
    assert "The items add up to £42.00, but the receipt total is £56.00." in text
    assert button(at, "Continue to split").disabled
    at.checkbox[0].check().run()
    assert not button(at, "Continue to split").disabled


def test_manual_entry_and_people_validation(app):
    at = app
    button(at, "Enter items manually").click().run()
    assert button(at, "Continue to split").disabled
    name_key = keys(at.text_input, "item_name_")[0]
    price_key = keys(at.number_input, "item_price_")[0]
    at.text_input(key=name_key).input("Shared platter").run()
    at.number_input(key=price_key).set_value(10.0).run()
    button(at, "Continue to split").click().run()
    assert "No one added yet" in page_text(at)
    for name in ("A", "B", "C"):
        at.text_input(key="new_person").input(name)
        button(at, "Add").click().run()
    assert "£3.34" in page_text(at) and page_text(at).count("£3.33") >= 2
    at.text_input(key="new_person").input("   ")
    button(at, "Add").click().run()
    assert "Enter a name." in page_text(at)


def test_extraction_failure_message(app, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "x")

    def fail(*a, **k):
        raise gemma.GemmaError("No items could be read from that receipt.")

    monkeypatch.setattr(gemma, "make_client", lambda key=None: object())
    monkeypatch.setattr(gemma, "read_receipt", fail)
    at = AppTest.from_file(APP, default_timeout=30).run()
    start_sample(at)
    button(at, "Read this sample with Gemma 4").click().run()
    assert "We couldn't read this receipt. Try a clearer image or enter the items manually." in page_text(at)
