"""Small accessible HTML building blocks. Styling lives in theme.py (DESIGN.md tokens).
Every piece of user-supplied text is escaped before it is placed in HTML."""

from __future__ import annotations

import html

PUMPKIN = '<span class="ss-icon pumpkin" aria-hidden="true"></span>'
GHOST = '<span class="ss-icon ghost" aria-hidden="true"></span>'
STEPS = ["Add", "Review", "Export"]
SR_ONLY = 'style="position:absolute;left:-9999px"'


def e(text) -> str:
    return html.escape(str(text))


def brand() -> str:
    return (
        '<div class="ss-brand">' + PUMPKIN +
        '<div><p class="ss-name">Summon<span class="ss-label">Fusion hackathon prototype</span></p>'
        '<div class="ss-tagline">Screenshots in. Calendar out.</div></div></div>'
    )


def page_title() -> str:
    return (
        '<h1 class="ss-title">Add plans to your calendar</h1>'
        '<p class="ss-desc">Upload a timetable, screenshot, poster or PDF. Check the events, then add them to any calendar.</p>'
    )


def steps(current: int) -> str:
    """current: 0 Add, 1 Review, 2 Export, 3 all done."""
    items = []
    for i, name in enumerate(STEPS):
        if i < current:
            state, attr, num, sr = "done", "", "✓", " (completed)"
        elif i == current:
            state, attr, num, sr = "current", ' aria-current="step"', str(i + 1), " (current step)"
        else:
            state, attr, num, sr = "", "", str(i + 1), ""
        items.append(
            f'<li class="ss-step {state}"{attr}><span class="ss-step-num" aria-hidden="true">{num}</span>'
            f"{name}<span {SR_ONLY}>{sr}</span></li>"
        )
    return f'<nav aria-label="Progress"><ol class="ss-steps">{"".join(items)}</ol></nav>'


def heading(text: str, desc: str | None = None) -> str:
    out = f'<h2 class="ss-h2">{e(text)}</h2>'
    if desc:
        out += f'<p class="ss-support">{e(desc)}</p>'
    return out


def subheading(text: str) -> str:
    return f'<h3 class="ss-h3">{e(text)}</h3>'


def notice(text: str, kind: str = "info", title: str | None = None) -> str:
    """kind: info, success, warning, error. The title word means status never relies on colour alone."""
    prefix = title or {"info": "Note", "success": "Done", "warning": "Check", "error": "Error"}[kind]
    role = 'role="alert"' if kind == "error" else 'role="status" aria-live="polite"'
    return f'<div class="ss-notice {kind}" {role}><b>{e(prefix)}:</b><span>{e(text)}</span></div>'


def badge(text: str, neutral: bool = False) -> str:
    return f'<span class="ss-badge{" neutral" if neutral else ""}">{e(text)}</span>'


def source_name(name: str) -> str:
    return f'<p class="ss-merchant">{e(name)}</p>'


def event_list(rows: list[tuple[str, str, str]], caption: str) -> str:
    """rows: (title, when, where). A simple, readable summary table."""
    body = "".join(
        f'<tr><td><span class="ss-person-name">{e(t)}</span>'
        f'<span class="detail">{e(w)}{(" · " + e(p)) if p else ""}</span></td></tr>'
        for t, w, p in rows
    )
    return (
        f'<table class="ss-people"><caption {SR_ONLY}>{e(caption)}</caption>'
        f'<thead><tr><th scope="col">Event</th></tr></thead><tbody>{body}</tbody></table>'
    )


def empty_events() -> str:
    return f'<div class="ss-empty">{GHOST}<span>No events yet. Add one below, or go back and try another file.</span></div>'
