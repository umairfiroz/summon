---
name: summon
description: Turns screenshots, photos, timetables, posters, group-chat messages and PDFs (such as coursework briefs) into a standard .ics calendar file that imports into Google Calendar, Apple Calendar or Outlook. Use when the user shares an image or document with dates, times, deadlines or a university timetable and wants the events in their calendar.
license: MIT
compatibility: Needs a vision-capable model to read images (built and tested with the open-weight Gemma 4), Python 3.10+, and `pip install icalendar tzdata` for scripts/make_ics.py.
metadata:
  author: umairfiroz
  version: "1.0"
  source: https://github.com/umairfiroz/hacktoberfest26
---

# Summon

Read events from what the user shares, confirm them, then build the calendar file with
`scripts/make_ics.py`. Never write the .ics by hand: the script handles time zones,
daylight-saving changes, repeating events, skipped weeks and reminders correctly.

## Steps

1. **Find today's date and the user's time zone.** Relative dates ("tomorrow", "next Friday")
   are worked out from today. UK numeric dates are day/month (03/04 is 3 April).
2. **Read the input.** For each event note the title, date, start and end time, location,
   and whether it's a deadline. A deadline has a due time but no end. Something with a date
   and no time is all day. Only include what is actually there. Never invent times or places.
3. **University timetables with week numbers** ("Weeks 1-10, 12"): record the weekday and
   the weeks exactly as written, and ask the user for the **Monday of week 1** from their
   university's term dates. Don't guess it.
4. **Say what you weren't sure about.** If a time is unreadable or a date could be read two
   ways, tell the user and ask rather than guessing silently.
5. **Show the user the list** (title, when, where) and let them correct it.
6. **Write the event JSON** described in [references/events-schema.md](references/events-schema.md).
   Deadlines get `"reminder_minutes": 1440` (one day) unless the user says otherwise.
7. **Build the file:**

   ```bash
   python scripts/make_ics.py events.json summon-events.ics
   ```

   If it prints `error: …`, fix that event and run it again. It won't write a partial file.
8. **Tell the user how to import it:** Google Calendar → Settings → Import & export → Import;
   Apple Calendar → open the file; Outlook → Add calendar → Upload from file. Importing twice
   creates duplicates.

## Example

User shares a timetable row "Monday 09:00-11:00 Software Engineering, Building 32 / Room 1015,
Weeks 1-10, 12" and says week 1 starts on Monday 28 September 2026.

```json
{"timezone": "Europe/London", "week1": "2026-09-28",
 "events": [{"title": "Software Engineering lecture", "repeat": "teaching_weeks", "weekday": "Monday",
             "weeks": "1-10, 12", "start": "09:00", "end": "11:00", "location": "Building 32 / Room 1015"}]}
```

Output: `Software Engineering lecture: Mon 09:00–11:00 · weeks 1-10, 12 (11 times)`. Week 11 is
skipped and every lecture stays at 09:00 local time across the October clock change.

## Edge cases

- No end time for an event: it becomes one hour long. Say so.
- "Every Tuesday" with no end date: ask when it stops, or add it once and say so.
- Times like "24:00" are written as 23:59 on the same day.
- Scanned PDFs have no text layer: read the page images instead.
