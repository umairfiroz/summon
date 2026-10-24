"""Small HTML building blocks for the Split & Spell interface.

All styling lives in theme.py and uses the DESIGN.md tokens. Every piece of
user-supplied text is escaped before it is placed in HTML.
"""

from __future__ import annotations

import html
import json

# Outline icons are drawn with CSS masks in theme.py so they use token colours.
PUMPKIN = '<span class="ss-icon pumpkin" aria-hidden="true"></span>'
GHOST = '<span class="ss-icon ghost" aria-hidden="true"></span>'

STEPS = ["Upload", "Review", "Split"]


def e(text) -> str:
    return html.escape(str(text))


def brand() -> str:
    return (
        '<div class="ss-brand">' + PUMPKIN +
        '<div><p class="ss-name">Split &amp; Spell<span class="ss-label">Fusion hackathon prototype</span></p>'
        '<div class="ss-tagline">Receipts in. Fair shares out.</div></div></div>'
    )


def page_title() -> str:
    return (
        '<h1 class="ss-title">Split your dinner receipt</h1>'
        '<p class="ss-desc">Check the items, choose a split, and see who owes what.</p>'
    )


def steps(current: int) -> str:
    """current: 0 Upload, 1 Review, 2 Split, 3 all done."""
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
            f'{name}<span style="position:absolute;left:-9999px">{sr}</span></li>'
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


def merchant(name: str | None) -> str:
    return f'<p class="ss-merchant">{e(name or "Unknown merchant")}</p>'


def reconciliation(rows: list[tuple[str, str]], total_label: str, total_value: str,
                   after: list[tuple[str, str]] | None = None) -> str:
    """Totals table: breakdown rows, a bold total row, then optional reference rows."""
    body = "".join(f'<tr><td>{e(a)}</td><td class="money">{e(b)}</td></tr>' for a, b in rows)
    body += f'<tr class="total"><td>{e(total_label)}</td><td class="money">{e(total_value)}</td></tr>'
    body += "".join(f'<tr class="ref"><td>{e(a)}</td><td class="money">{e(b)}</td></tr>' for a, b in (after or []))
    return f'<table class="ss-recon" aria-label="Bill totals">{body}</table>'


def initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    if not parts:
        return "?"
    letters = parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")
    return letters.upper()


def people_table(rows: list[tuple[str, str, str | None]], caption: str) -> str:
    """rows: (name, amount, optional detail line)."""
    body = ""
    for name, amount, detail in rows:
        detail_html = f'<span class="detail">{e(detail)}</span>' if detail else ""
        body += (
            f'<tr><td><div class="ss-person"><span class="ss-avatar" aria-hidden="true">{e(initials(name))}</span>'
            f'<span class="ss-person-name">{e(name)}{detail_html}</span></div></td>'
            f'<td class="money">{e(amount)}</td></tr>'
        )
    return (
        f'<table class="ss-people"><caption style="position:absolute;left:-9999px">{e(caption)}</caption>'
        f'<thead><tr><th scope="col">Person</th><th scope="col" class="money">Amount owed</th></tr></thead>'
        f"<tbody>{body}</tbody></table>"
    )


def main_amount(label: str, value: str) -> str:
    return f'<div class="ss-amount-label">{e(label)}</div><div class="ss-amount">{e(value)}</div>'


def empty_people() -> str:
    return f'<div class="ss-empty">{GHOST}<span>No one added yet. Add the people sharing this bill.</span></div>'


def copy_button(summary: str) -> str:
    """Clipboard button with "Summary copied" feedback and a visible failure message."""
    payload = json.dumps(summary)
    return f"""
<div class="ss-copy-row">
  <button type="button" class="ss-copy-btn" id="ss-copy">Copy summary</button>
  <span class="ss-copy-status" id="ss-copy-status" role="status" aria-live="polite"></span>
</div>
<script>
(function () {{
  var btn = document.getElementById("ss-copy"), status = document.getElementById("ss-copy-status");
  if (!btn) return;
  btn.onclick = function () {{
    var text = {payload};
    if (!navigator.clipboard) {{ status.textContent = "Copying isn't available here. Select the summary text below instead."; return; }}
    navigator.clipboard.writeText(text).then(function () {{ status.textContent = "Summary copied"; }},
      function () {{ status.textContent = "Couldn't copy automatically. Select the summary text below instead."; }});
  }};
}})();
</script>"""
