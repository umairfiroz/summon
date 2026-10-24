# Summon

**Screenshots in. Calendar out.**

Summon turns the plans buried in screenshots, photos, posters, university timetables, group
chats and coursework PDFs into calendar events. You upload a file, check what the open-weight
**Gemma 4** model found, and download one calendar file that works with Google Calendar, Apple
Calendar and Outlook.

Built solo at **Hacktoberfest Southampton 2026** (theme: *Fusion*). It fuses two tools everyone
already uses, a document reader and a calendar, so you no longer retype events by hand.

## What it does

1. **Add.** Upload up to 5 PNG, JPG, WEBP or PDF files at once. You can also try one of three labelled samples or add events manually.
2. **Review.** Gemma 4 finds events and deadlines and works out relative dates ("tomorrow", "fri 30th") from today. It flags anything it wasn't sure about, and you can correct every field.
3. **Export.** Download a standard `.ics` file, or add simple events to Google Calendar one at a time.

It handles:

- **University timetables with teaching weeks.** "Weeks 1-10, 12" becomes one repeating event that skips week 11, counted from the Monday you set as week 1.
- **Coursework briefs (PDF).** Every deadline becomes a "Due:" event with a reminder one day before. Text PDFs are read as text; scanned PDFs are read as images.
- **Daylight saving.** A 09:00 lecture stays at 09:00 after the clocks change.
- **Light, Dark and System themes,** remembered in your browser.

## How the AI is used

| Step | Model | Input → output |
|---|---|---|
| Find events | Gemma 4 (`gemma-4-26b-a4b-it` by default) | Images and/or PDF text, plus today's date and time zone → JSON events (title, date, times, location, teaching weeks, deadline or event, and a note on anything uncertain) |

Gemma's output is validated field by field. Anything that can't be read is left blank and
explained, never silently guessed. The raw output is shown under "What Gemma 4 extracted".
The calendar file itself is built by plain, tested code (`summon/calendar_export.py`), so time
zones, repeats and skipped weeks are always correct.

**Privacy:** files are sent to Google's Gemini API only when you click *Find events*. Summon
doesn't store files or events, and only your theme choice is saved in the browser.

## Model and licence

- **Model:** [Gemma 4](https://ai.google.dev/gemma/docs/core) by Google DeepMind, an open-weight model family. The default `gemma-4-26b-a4b-it` is a 26B-parameter Mixture-of-Experts model with about 4B active parameters. Set `GEMMA_MODEL=gemma-4-31b-it` to use the dense 31B model.
- **Model licence:** [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0). See the [Gemma docs](https://ai.google.dev/gemma/docs/core) for the model card and terms.
- **Access:** through the [Gemini API](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api), with a free key from [Google AI Studio](https://aistudio.google.com).
- **This project:** [MIT](LICENSE).

## Key dependencies

| Package | Purpose | Licence |
|---|---|---|
| [streamlit](https://github.com/streamlit/streamlit) | Web UI | Apache 2.0 |
| [google-genai](https://github.com/googleapis/python-genai) | Gemini API client for Gemma 4 | Apache 2.0 |
| [icalendar](https://github.com/collective/icalendar) | Writing standard .ics files with time zones | BSD-2-Clause |
| [pypdfium2](https://github.com/pypdfium2-team/pypdfium2) | Reading PDF text and rendering scanned pages | Apache 2.0 / BSD-3-Clause |
| [Pillow](https://github.com/python-pillow/Pillow) | Fixing photo rotation and size | MIT-CMU |
| [tzdata](https://github.com/python/tzdata) | Time zone data (needed on Windows) | Apache 2.0 |
| Inter font, self-hosted via [Fontsource](https://fontsource.org) | Typography that works offline | SIL OFL 1.1 |

## Run it

Python 3.10+ is required.

```bash
git clone https://github.com/umairfiroz/hacktoberfest26.git
cd hacktoberfest26
python -m venv .venv
# Windows:  .venv\Scripts\Activate.ps1      macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

To read your own files, set a Gemini API key (`GEMINI_API_KEY`) or paste one into the app.
The samples and manual entry work without a key.

### Try it in 30 seconds

Click **Sample timetable**, then **Continue to export**, and download the file. You'll get 46
calendar entries for 5 timetabled classes, with the skipped weeks left out. The samples are preloaded and
labelled. Click **Read this sample with Gemma 4**, or upload your own screenshot, to see live
extraction.

### Deploy your own copy (free)

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io), click **Create app**, and choose the repo with `app.py`.
3. Under **Advanced settings → Secrets**, add `GEMINI_API_KEY = "your-key"`.

Requests from your deployed app then use your key's free quota.

## Use it as an agent skill

[`skills/summon`](skills/summon) follows the [Agent Skills open standard](https://agentskills.io/specification)
and passes the `skills-ref` validator. An agent reads the image with its own vision model, confirms the
events with the user, and builds the file with the same tested logic:

```bash
pip install icalendar tzdata
python skills/summon/scripts/make_ics.py events.json summon-events.ics
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

There are 41 tests. They check every exported file with an independent recurrence parser
(`recurring-ical-events`). Coverage includes teaching weeks across the October clock change,
skipped weeks, weekly repeats, all-day and deadline events, reminders, text escaping, stable UIDs,
Google link limits, week-number parsing, relative-date prompting, malformed model output, text
and scanned PDFs, network failures, and all three samples through the real UI. They also check
that switching theme doesn't lose edits.

## Project structure

```
app.py                       Streamlit app: add → review → export
summon/gemma.py              Gemma 4 calls, PDF handling, validation of model output
summon/events.py             Event model, teaching weeks, repeats, validation (no AI, no UI)
summon/calendar_export.py    .ics and Google Calendar links
summon/theme.py              Design tokens, Light/Dark/System styles, theme persistence
summon/ui.py                 Small accessible HTML components
summon/sample.py             Labelled demo samples (files in assets/)
skills/summon/               Agent Skill version
DESIGN.md                    Design specification
tests/                       pytest suite
```
