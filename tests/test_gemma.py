from types import SimpleNamespace

import pytest

from split_and_spell import gemma


def test_extract_json_variants():
    assert gemma.extract_json('{"a": 1}') == {"a": 1}
    assert gemma.extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert gemma.extract_json('Sure! Here it is: {"a": [1, 2]} hope that helps') == {"a": [1, 2]}
    assert gemma.extract_json('[{"name": "Ali"}]') == [{"name": "Ali"}]
    with pytest.raises(ValueError):
        gemma.extract_json("no json here")


def test_parse_receipt_normalises():
    r = gemma.parse_receipt({
        "merchant": "The Crypt Cafe", "currency": "gbp",
        "items": [
            {"name": "Latte", "quantity": 2, "line_total": "7.80"},
            {"name": "Bad", "line_total": None},
            {"name": "Promo", "line_total": -1.5},
        ],
        "total": "£71.94", "discount": -3,
    })
    assert [i.name for i in r.items] == ["Latte", "Promo"]
    assert r.items[0].line_total == 7.80
    assert r.total == 71.94
    assert r.discount == 3
    assert r.symbol == "£"


def test_parse_receipt_errors():
    with pytest.raises(gemma.GemmaError):
        gemma.parse_receipt({"error": "not a receipt"})
    with pytest.raises(gemma.GemmaError):
        gemma.parse_receipt({"items": []})


class FakeModels:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def generate_content(self, model, contents):
        self.calls += 1
        return SimpleNamespace(text=self.replies.pop(0))


def fake_client(*replies):
    return SimpleNamespace(models=FakeModels(replies))


def test_network_failure_becomes_friendly_error():
    class Boom:
        def generate_content(self, model, contents):
            raise ConnectionError("no route")

    with pytest.raises(gemma.GemmaError, match="internet"):
        gemma._generate(SimpleNamespace(models=Boom()), "m", "x")


def test_read_receipt_retries_on_bad_json(tmp_path):
    from PIL import Image
    import io

    buf = io.BytesIO()
    Image.new("RGB", (50, 50), "white").save(buf, format="PNG")
    client = fake_client("not json", '{"items": [{"name": "Tea", "line_total": 2}], "total": 2}')
    r = gemma.read_receipt(client, buf.getvalue())
    assert r.items[0].name == "Tea" and client.models.calls == 2


def test_prepare_image_rejects_non_images():
    with pytest.raises(gemma.GemmaError):
        gemma.prepare_image(b"definitely not an image")
