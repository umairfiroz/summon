# Event JSON for `scripts/make_ics.py`

```json
{
  "timezone": "Europe/London",
  "week1": "2026-09-28",
  "events": [
    {"title": "Software Engineering lecture", "repeat": "teaching_weeks", "weekday": "Monday",
     "weeks": "1-10, 12", "start": "09:00", "end": "11:00", "location": "Building 32 / Room 1015"},
    {"title": "Design report", "kind": "deadline", "date": "2026-11-13", "start": "16:00",
     "reminder_minutes": 1440},
    {"title": "Halloween social", "date": "2026-10-30", "start": "19:30"},
    {"title": "Drop-in help", "date": "2026-11-03", "start": "15:00", "end": "16:00",
     "repeat": "weekly", "until": "2026-11-24"},
    {"title": "Reading week", "date": "2026-11-02", "all_day": true}
  ]
}
```

| Field | Meaning |
|---|---|
| `timezone` | IANA time zone for all times. Default `Europe/London`. |
| `week1` | Monday of teaching week 1. Required only if an event uses `teaching_weeks`. |
| `title` | Required. |
| `kind` | `event` (default) or `deadline`. Deadlines are written as "Due: …" with no duration. |
| `date` | `YYYY-MM-DD`. Required unless `repeat` is `teaching_weeks`. |
| `start`, `end` | `HH:MM`, 24-hour. Events without `end` last one hour. Omit both and set `all_day`. |
| `all_day` | `true` for date-only events. |
| `repeat` | `none` (default), `weekly` (needs `until`), or `teaching_weeks` (needs `weekday`, `weeks`, and `week1`). |
| `weeks` | Week numbers as written on the timetable, e.g. `1-10, 12`. Gaps become exceptions. |
| `reminder_minutes` | Minutes before the start to show a reminder. |
| `location`, `notes` | Optional text. |

The script refuses to write a file if any event is incomplete, and prints the reason.
