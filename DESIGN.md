# DESIGN.md — Summon

Summon reuses the Split & Spell design system (colour tokens, type, spacing, theme modes).
The original Split & Spell spec is kept on the `split-and-spell` branch.

## 1. Product and scope

Summon fuses two tools people already use, a screenshot or document reader and a calendar,
into one workflow. Hackathon theme: Fusion.

Tagline: "Screenshots in. Calendar out."

Core flow:
1. Add: upload screenshots, photos or PDFs (up to 5 at once), try a labelled sample, or add events manually.
2. Review: check and correct every event Gemma 4 found.
3. Export: download one standard .ics file, or add simple events to Google Calendar one at a time.

Supported inputs: university timetables (including teaching-week numbers), posters, group chats,
emails and coursework briefs (PDF deadlines).

Do not add accounts, calendar sync, chat or unrelated features without approval.
Only expose features that work. Label sample data honestly.

## 2. Visual direction

Practical, calm, friendly and slightly autumnal. Halloween is a restrained accent:
- One small pumpkin outline next to the product name.
- At most one subtle ghost outline, in the empty state.
- Warm neutral surfaces and burnt-orange accents.

Avoid neon, gradients, glow, glassmorphism, pure black, horror typography, animated decoration,
oversized marketing headings, emoji navigation and unclear labels.

## 3. Theme modes

Light, Dark and System, chosen with a labelled three-option control in the header.
- Default on first visit: System, which follows the operating system live.
- An explicit Light or Dark choice overrides the system preference.
- Persist only the theme, in localStorage under `summon-theme`.
- Changing theme never resets files, events or edits.
- Uploaded images and PDF previews are never recoloured.

## 4. Semantic colour tokens

Identical to Split & Spell. Implemented in `summon/theme.py` and `.streamlit/config.toml`.

| Token | Light | Dark |
|---|---|---|
| background | #F7F5EF | #1C1D1B |
| surface | #FFFFFF | #252622 |
| surface-subtle | #F0EDE5 | #2D2E29 |
| text-primary | #222320 | #F3F1E9 |
| text-secondary | #62645C | #B9BCAF |
| border | #DEDCD3 | #45473F |
| primary | #B84E19 | #F0A06A |
| primary-hover | #993E12 | #F5B58A |
| on-primary | #FFFFFF | #1C1D1B |
| primary-soft | #F9E9DE | #463023 |
| on-primary-soft | #913B12 | #F3B68D |
| success-text | #3E624B | #B5D4BA |
| success-background | #EDF3EC | #26372B |
| warning-text | #775118 | #F2CF8D |
| warning-background | #FFF3DB | #3B3222 |
| error-text | #A12D2D | #F1AEAE |
| error-background | #FBEDED | #41292A |
| focus-ring | #B84E19 | #F0A06A |

Every text/background pair used meets WCAG AA (4.5:1) in both themes. Status is never shown by
colour alone: notices start with a word ("Check:", "Ready:", "Error:").

## 5. Typography, spacing and shape

Inter (self-hosted, works offline) with system-ui fallbacks. Page title 30/38 bold, section
heading 20/28 semibold, body 16/24, supporting 14/20, labels 12/18. Sentence case, left-aligned.
Spacing 4–64px scale; panels 12px radius, inputs and buttons 8px. Thin borders, no shadows.

## 6. Layout

Header: pumpkin, product name, tagline, "Fusion hackathon prototype" label, theme control.
Page title: "Add plans to your calendar". Progress: 1 Add / 2 Review / 3 Export.
Review and Export: two columns (about 38% source preview, 62% work area); single column on phones.

## 7. Add

Heading "Start with a screenshot or PDF". Choose up to 5 PNG, JPG, WEBP or PDF files (10 MB each).
Explain that files go to Google's Gemini API. Show the time zone and the date used for relative
dates. Loading text: "Finding events…". Failure: "We couldn't find events in this file. Try a
clearer image, or add the events manually." plus the specific reason.

## 8. Review

Each event is a collapsible row whose label summarises it ("Mon 09:00–11:00 · weeks 1-10, 12
(11 times)"). Rows that need fixing say "Needs attention" and open automatically. Anything Gemma
was unsure about is shown as "Gemma wasn't sure: …". Never invent confidence scores.

Fields: add to calendar, type (Event / Deadline), title, repeats (Doesn't repeat / Every week /
Teaching weeks), date or day + weeks, all day, start/due time, end, location, reminder, notes.

Teaching weeks need "Week 1 starts on (a Monday)". Never guess it; samples say their value is a sample.
Continue is blocked, with the reason in words, until every included event is complete.

## 9. Export

"Your calendar file is ready" with the count of events and calendar entries and the time zone.
One primary action: "Download calendar file (.ics)". Short import instructions for Google, Apple
and Outlook, and a duplicate warning. Per-event Google links only where the link can represent
the event exactly; otherwise say to use the file.

## 10. Calendar correctness

- Times are written with the user's time zone and a VTIMEZONE, so repeats keep their local time
  across daylight-saving changes.
- All-day events use an exclusive end date. Deadlines are zero-length and don't block time.
- Teaching weeks become one weekly RRULE with EXDATEs for gaps; UNTIL is in UTC (RFC 5545).
- Events without an end time last one hour, shown in the summary before export.
- Stable UIDs, so the same export produces the same events.

## 11. Accessibility, privacy and resilience

Keyboard-operable controls, visible focus, explicit labels, live-region notices, no colour-only
meaning, comfortable touch targets, no horizontal scrolling on phones. Files are sent to the
Gemini API only when the user asks; nothing is stored after the page closes; only the theme
choice is persisted.
