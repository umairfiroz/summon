"""Everything that talks to Gemma 4 through the Gemini API.

extract_events() sends screenshots, photos or PDF text to Gemma 4 and returns
validated event data. Dates and times are checked here and again in the review
screen; the calendar file itself is built by plain code in calendar_export.py.
"""

from __future__ import annotations

import io
import json
import os
import re
import time
from datetime import date, datetime

from google import genai
from google.genai import errors, types
from PIL import Image, ImageOps

DEFAULT_MODEL = os.environ.get("GEMMA_MODEL", "gemma-4-26b-a4b-it")
RETRYABLE_CODES = {429, 500, 502, 503, 504}
MAX_PDF_PAGES = 20
MAX_PDF_CHARS = 60_000
MIN_TEXT_CHARS = 200  # below this a PDF is treated as scanned and sent as images


class GemmaError(RuntimeError):
    """A user-friendly error to show in the UI."""


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




# --------------------------------------------------------------------------- #
# PDFs
# --------------------------------------------------------------------------- #

def pdf_to_parts(pdf_bytes: bytes) -> tuple[list, str]:
    """Return (content parts, description). Text PDFs are sent as text; scanned PDFs
    are rendered to images. Raises GemmaError for unreadable files."""
    import pypdfium2 as pdfium

    try:
        pdf = pdfium.PdfDocument(pdf_bytes)
    except Exception as exc:
        raise GemmaError("That PDF couldn't be opened. It may be damaged or password-protected.") from exc
    try:
        pages = min(len(pdf), MAX_PDF_PAGES)
        texts = []
        for i in range(pages):
            textpage = pdf[i].get_textpage()
            texts.append(textpage.get_text_range())
            textpage.close()
        joined = "\n\n".join(f"--- Page {i + 1} ---\n{t.strip()}" for i, t in enumerate(texts))
        note = f"{pages} page{'s' if pages != 1 else ''}" + (f" (first {MAX_PDF_PAGES} of {len(pdf)})" if len(pdf) > pages else "")
        if sum(len(t.strip()) for t in texts) >= MIN_TEXT_CHARS:
            return [f"Document text:\n{joined[:MAX_PDF_CHARS]}"], f"Text from {note}"
        images = []
        for i in range(min(pages, 5)):
            bitmap = pdf[i].render(scale=2).to_pil()
            buf = io.BytesIO()
            bitmap.convert("RGB").save(buf, format="JPEG", quality=85)
            images.append(types.Part.from_bytes(data=prepare_image(buf.getvalue()), mime_type="image/jpeg"))
        return images, f"Images of {min(pages, 5)} scanned page(s)"
    finally:
        pdf.close()


def pdf_preview(pdf_bytes: bytes) -> bytes | None:
    """PNG of the first page, for the preview panel."""
    import pypdfium2 as pdfium

    try:
        pdf = pdfium.PdfDocument(pdf_bytes)
        image = pdf[0].render(scale=1.5).to_pil()
        pdf.close()
    except Exception:
        return None
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Event extraction
# --------------------------------------------------------------------------- #

PROMPT = """You find calendar events and deadlines in screenshots, photos, posters, timetables,
messages and documents.

Today is {today_long} ({today_iso}). The user's time zone is {tz}. The user is in the UK,
so numeric dates are DAY/MONTH (03/04 means 3 April).

Return ONLY a JSON object, no markdown:
{{"events": [
  {{
    "title": short, specific title (e.g. "COMP2300 lecture", "Coursework 1 deadline"),
    "kind": "event" or "deadline",
    "date": "YYYY-MM-DD" or null,
    "start": "HH:MM" 24-hour or null,
    "end": "HH:MM" 24-hour or null,
    "all_day": true or false,
    "location": string or null,
    "notes": one short line of useful detail or null,
    "weekday": "Monday".."Sunday" or null,
    "weeks": teaching weeks exactly as written, e.g. "1-10, 12", or null,
    "repeat_weekly_until": "YYYY-MM-DD" or null,
    "unclear": short reason if a date, time or detail is ambiguous or guessed, else null
  }}
]}}

Rules:
- Only include things that are actually in the input. Never invent events, times or places.
- Resolve relative dates ("tomorrow", "next Friday", "this Wednesday") from today's date.
- If a date has no year, use the next time that date occurs on or after today.
- University timetable entries that list week numbers: set "weekday" and "weeks", and set "date" to null.
- Something that happens every week without week numbers: set "date" to the first occurrence and
  "repeat_weekly_until" if an end is given; otherwise treat it as a single event and say so in "unclear".
- Deadlines, due dates and submission times are kind "deadline"; use the due time as "start" and no "end".
  A deadline with a date but no time is "all_day": true.
- An event with a date but no time is "all_day": true.
- Write "unclear" whenever you had to guess (for example an unreadable time or a date that could be
  read two ways). Do not hide uncertainty.
- If there are no events, return {{"events": []}}.
"""

WEEKDAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _clean_str(value, limit: int) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()[:limit] if value not in (None, "") else ""


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None


def _parse_time(value):
    if not value:
        return None
    match = re.fullmatch(r"\s*(\d{1,2})[:.](\d{2})\s*", str(value))
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour == 24 and minute == 0:
        hour, minute = 23, 59
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    from datetime import time as dtime
    return dtime(hour, minute)


def parse_events(data) -> list[dict]:
    """Validate Gemma's JSON into plain dicts for the events module. Bad fields become
    None and are explained in "unclear" rather than silently fixed."""
    if isinstance(data, list):
        data = {"events": data}
    if not isinstance(data, dict) or not isinstance(data.get("events"), list):
        raise GemmaError("Gemma's answer wasn't in the expected format.")
    results = []
    for raw in data["events"]:
        if not isinstance(raw, dict):
            continue
        issues = []
        title = _clean_str(raw.get("title"), 120)
        kind = "deadline" if str(raw.get("kind", "")).lower() == "deadline" else "event"
        event_date = _parse_date(raw.get("date"))
        if raw.get("date") and event_date is None:
            issues.append(f"date “{raw.get('date')}” couldn't be read")
        start = _parse_time(raw.get("start"))
        if raw.get("start") and start is None:
            issues.append(f"start time “{raw.get('start')}” couldn't be read")
        end = _parse_time(raw.get("end"))
        if raw.get("end") and end is None:
            issues.append(f"end time “{raw.get('end')}” couldn't be read")
        weekday_name = str(raw.get("weekday") or "").strip().lower()
        weekday = WEEKDAY_NAMES.index(weekday_name) if weekday_name in WEEKDAY_NAMES else None
        weeks = _clean_str(raw.get("weeks"), 60)
        until = _parse_date(raw.get("repeat_weekly_until"))
        all_day = bool(raw.get("all_day")) or (start is None and (event_date is not None or bool(weeks)))
        if weeks:
            repeat = "teaching_weeks"
        elif until and event_date and until > event_date:
            repeat = "weekly"
        else:
            repeat = "none"
        if repeat == "teaching_weeks" and start is not None:
            all_day = False
        unclear = _clean_str(raw.get("unclear"), 200)
        if issues:
            unclear = "; ".join(filter(None, [unclear] + issues))
        if not title and not event_date and not weeks:
            continue
        results.append({
            "title": title, "kind": kind, "date": event_date, "start": start, "end": end,
            "all_day": all_day and start is None, "location": _clean_str(raw.get("location"), 120),
            "notes": _clean_str(raw.get("notes"), 300), "repeat": repeat, "until": until if repeat == "weekly" else None,
            "weekday": weekday, "weeks": weeks, "unclear": unclear or None,
        })
    return results


def extract_events(client, parts: list, today: date, tz: str, model: str = DEFAULT_MODEL) -> tuple[list[dict], dict]:
    """Send content parts (images and/or text) to Gemma. Returns (events, raw JSON)."""
    prompt = PROMPT.format(today_long=f"{today:%A} {today.day} {today:%B %Y}", today_iso=today.isoformat(), tz=tz)
    contents = list(parts) + [prompt]
    text = _generate(client, model, contents)
    try:
        data = extract_json(text)
    except ValueError:
        text = _generate(client, model, contents[:-1] + [prompt + "\nYour last answer was not valid JSON. Output ONLY the JSON object."])
        try:
            data = extract_json(text)
        except ValueError as exc:
            raise GemmaError("Gemma's answer couldn't be understood.") from exc
    return parse_events(data), data


def image_part(image_bytes: bytes):
    return types.Part.from_bytes(data=prepare_image(image_bytes), mime_type="image/jpeg")
