"""Everything that talks to Gemma 4 through the Gemini API.

read_receipt() sends a receipt photo to Gemma 4 and returns validated,
structured items and totals. All money maths is done in split.py, never by
the model, so amounts shown to users are always exact.
"""

from __future__ import annotations

import io
import json
import os
import re
import time
from dataclasses import dataclass

from google import genai
from google.genai import errors, types
from PIL import Image, ImageOps

DEFAULT_MODEL = os.environ.get("GEMMA_MODEL", "gemma-4-26b-a4b-it")
MODELS = {
    "gemma-4-26b-a4b-it": "Gemma 4 26B A4B (fast, Mixture-of-Experts)",
    "gemma-4-31b-it": "Gemma 4 31B (dense, slower, sometimes more accurate)",
}

CURRENCY_SYMBOLS = {
    "GBP": "£", "EUR": "€", "USD": "$", "CAD": "$", "AUD": "$",
    "INR": "₹", "JPY": "¥", "SAR": "SAR ", "AED": "AED ", "PKR": "Rs ",
}

RETRYABLE_CODES = {429, 500, 502, 503, 504}

RECEIPT_PROMPT = """You are a meticulous receipt reader. Read the receipt in the image.

Return ONLY a JSON object (no markdown, no commentary) with exactly these keys:
{
  "merchant": string or null,
  "currency": ISO 4217 code such as "GBP", "EUR", "USD" (guess from symbols; default "GBP"),
  "items": [
    {"name": short item name, "quantity": number, "line_total": number}
  ],
  "subtotal": number or null,
  "tax_added": number or null,
  "service_charge": number or null,
  "tip": number or null,
  "discount": number or null,
  "total": number or null
}

Rules:
- "line_total" is the final price printed for that line (already multiplied by quantity).
- One entry per printed line. Do not merge or invent items.
- Include discount/promo lines that are printed against a specific item as items with a NEGATIVE line_total.
- "tax_added" is ONLY tax added on top of the subtotal (common in the US). UK VAT that is
  already included in prices must be null.
- "discount" is a whole-bill discount that is NOT already an item line, as a POSITIVE number.
- Numbers are plain decimals without currency symbols, e.g. 4.50.
- If something is unreadable, use your best guess for names and null for missing totals.
- If the image is not a receipt, return {"error": "not a receipt"}.
"""

class GemmaError(RuntimeError):
    """A user-friendly error to show in the UI."""


@dataclass
class ReceiptItem:
    name: str
    quantity: float
    line_total: float


@dataclass
class Receipt:
    merchant: str | None
    currency: str
    items: list[ReceiptItem]
    subtotal: float | None
    tax_added: float | None
    service_charge: float | None
    tip: float | None
    discount: float | None
    total: float | None
    raw: dict

    @property
    def symbol(self) -> str:
        return CURRENCY_SYMBOLS.get(self.currency, f"{self.currency} ")


# --------------------------------------------------------------------------- #
# Client & low-level helpers
# --------------------------------------------------------------------------- #

def make_client(api_key: str | None = None) -> genai.Client:
    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise GemmaError(
            "No Gemini API key found. Set the GEMINI_API_KEY environment variable "
            "or paste a key under “Gemini API key”."
        )
    return genai.Client(api_key=key)


def prepare_image(image_bytes: bytes, max_side: int = 2048) -> bytes:
    """Fix phone rotation, convert to RGB JPEG and shrink huge photos."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)
    except Exception as exc:  # Pillow raises many different exception types
        raise GemmaError("That file isn't an image that can be read. Use JPG, PNG or WEBP.") from exc
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((max_side, max_side))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=90)
    return out.getvalue()


def _generate(client: genai.Client, model: str, contents, attempts: int = 3) -> str:
    """Call the model with retries on rate limits / temporary server errors."""
    for attempt in range(1, attempts + 1):
        try:
            response = client.models.generate_content(model=model, contents=contents)
            text = response.text
            if not text:
                raise GemmaError("Gemma returned an empty answer.")
            return text
        except errors.APIError as exc:
            code = getattr(exc, "code", None)
            if code in RETRYABLE_CODES and attempt < attempts:
                time.sleep(2 ** attempt)
                continue
            if code == 429:
                raise GemmaError("The Gemini API rate limit was reached. Wait about a minute and try again.") from exc
            if code in (401, 403):
                raise GemmaError("The API key was rejected. Check GEMINI_API_KEY.") from exc
            if code == 404:
                raise GemmaError(f"Model '{model}' was not found. Set GEMMA_MODEL to another Gemma 4 model, such as gemma-4-31b-it.") from exc
            raise GemmaError(f"Gemini API error ({code}): {getattr(exc, 'message', exc)}") from exc
        except GemmaError:
            raise
        except Exception as exc:  # network failures, timeouts, SDK errors
            raise GemmaError("Couldn't reach the Gemini API. Check your internet connection.") from exc
    raise GemmaError("Gemma didn't respond.")  # pragma: no cover


def extract_json(text: str):
    """Pull the first JSON object/array out of a model reply (handles ```json fences)."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start, end = cleaned.find(open_ch), cleaned.rfind(close_ch)
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("No valid JSON found in model output.")


def _num(value) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:[.,]\d+)?", str(value).replace(",", ""))
    return float(match.group()) if match else None


def parse_receipt(data: dict) -> Receipt:
    """Validate and normalise the JSON Gemma returned."""
    if not isinstance(data, dict):
        raise GemmaError("Gemma's answer wasn't in the expected format.")
    if data.get("error"):
        raise GemmaError("That image doesn't look like a receipt.")

    items: list[ReceiptItem] = []
    for raw in data.get("items") or []:
        if not isinstance(raw, dict):
            continue
        price = _num(raw.get("line_total", raw.get("price")))
        if price is None:
            continue
        name = str(raw.get("name") or "Mystery item").strip()[:60]
        qty = _num(raw.get("quantity")) or 1
        items.append(ReceiptItem(name=name, quantity=qty, line_total=round(price, 2)))

    if not items:
        raise GemmaError("No items could be read from that receipt.")

    currency = str(data.get("currency") or "GBP").upper().strip()[:3] or "GBP"
    return Receipt(
        merchant=(str(data["merchant"]).strip() or None) if data.get("merchant") else None,
        currency=currency,
        items=items,
        subtotal=_num(data.get("subtotal")),
        tax_added=_num(data.get("tax_added")),
        service_charge=_num(data.get("service_charge")),
        tip=_num(data.get("tip")),
        discount=abs(_num(data.get("discount")) or 0) or None,
        total=_num(data.get("total")),
        raw=data,
    )


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def read_receipt(client: genai.Client, image_bytes: bytes, model: str = DEFAULT_MODEL) -> Receipt:
    """Send the receipt photo to Gemma and get back a validated Receipt."""
    jpeg = prepare_image(image_bytes)
    image_part = types.Part.from_bytes(data=jpeg, mime_type="image/jpeg")

    text = _generate(client, model, [image_part, RECEIPT_PROMPT])
    try:
        data = extract_json(text)
    except ValueError:
        # One retry asking for strict JSON.
        text = _generate(
            client, model,
            [image_part, RECEIPT_PROMPT + "\nYour last answer was not valid JSON. Output ONLY the JSON object."],
        )
        try:
            data = extract_json(text)
        except ValueError as exc:
            raise GemmaError("Gemma's answer couldn't be understood.") from exc
    return parse_receipt(data)
