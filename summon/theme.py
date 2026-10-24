"""Light / Dark / System theming for Summon.

Colour values come only from the semantic token table in DESIGN.md.

How it works in Streamlit:
* .streamlit/config.toml gives Streamlit's own [theme.light] and [theme.dark]
  the same tokens, so native widgets match in System mode.
* css(mode) re-applies the tokens to every widget the app uses, so an explicit
  Light or Dark choice wins even when the operating system prefers the other.
  In System mode it uses a prefers-color-scheme media query, so it follows OS
  changes live.
* persistence_script(mode) remembers the choice in localStorage under
  "summon-theme" and restores it on the next visit. Only the theme is
  stored, never your files or events.
"""

from __future__ import annotations

MODES = ["light", "dark", "system"]
MODE_LABELS = {"light": "Light", "dark": "Dark", "system": "System"}
STORAGE_KEY = "summon-theme"

TOKENS = {
    "light": {
        "background": "#F7F5EF", "surface": "#FFFFFF", "surface-subtle": "#F0EDE5",
        "text-primary": "#222320", "text-secondary": "#62645C", "border": "#DEDCD3",
        "primary": "#B84E19", "primary-hover": "#993E12", "on-primary": "#FFFFFF",
        "primary-soft": "#F9E9DE", "on-primary-soft": "#913B12",
        "success-text": "#3E624B", "success-background": "#EDF3EC",
        "warning-text": "#775118", "warning-background": "#FFF3DB",
        "error-text": "#A12D2D", "error-background": "#FBEDED",
        "focus-ring": "#B84E19",
    },
    "dark": {
        "background": "#1C1D1B", "surface": "#252622", "surface-subtle": "#2D2E29",
        "text-primary": "#F3F1E9", "text-secondary": "#B9BCAF", "border": "#45473F",
        "primary": "#F0A06A", "primary-hover": "#F5B58A", "on-primary": "#1C1D1B",
        "primary-soft": "#463023", "on-primary-soft": "#F3B68D",
        "success-text": "#B5D4BA", "success-background": "#26372B",
        "warning-text": "#F2CF8D", "warning-background": "#3B3222",
        "error-text": "#F1AEAE", "error-background": "#41292A",
        "focus-ring": "#F0A06A",
    },
}


def _vars(name: str) -> str:
    scheme = f"color-scheme: {name};"
    return scheme + "".join(f"--{k}: {v};" for k, v in TOKENS[name].items())


def token_block(mode: str) -> str:
    if mode == "light":
        return f":root {{ {_vars('light')} }}"
    if mode == "dark":
        return f":root {{ {_vars('dark')} }}"
    return (
        f":root {{ {_vars('light')} }}\n"
        f"@media (prefers-color-scheme: dark) {{ :root {{ {_vars('dark')} }} }}"
    )


# Component styles. Every colour is a token variable.
_COMPONENTS = """
/* ---------- shell ---------- */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
  background: var(--background) !important; color: var(--text-primary);
}
.stApp { font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
[data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stMainMenu"] { display: none !important; }
.block-container { max-width: 1200px !important; padding: 0 32px 64px !important; }
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stMarkdownContainer"] p,
.stApp [data-testid="stMarkdownContainer"] li, .stApp [data-testid="stWidgetLabel"],
.stApp [data-testid="stWidgetLabel"] p, .stApp label { color: var(--text-primary); }
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] p { color: var(--text-secondary) !important; opacity: 1 !important; }
.stApp a { color: var(--primary); }
.stApp hr { border-color: var(--border) !important; }
.stApp :focus-visible { outline: 2px solid var(--focus-ring) !important; outline-offset: 3px !important; }

/* ---------- panels (st.container with key "panel_*") ---------- */
[class*="st-key-panel_"] {
  background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 24px;
}
[class*="st-key-header"] { border-bottom: 1px solid var(--border); padding: 16px 0; margin-bottom: 32px; }
[class*="st-key-preview_area"] { background: var(--surface-subtle); border-radius: 8px; padding: 16px; }

/* ---------- text inputs & number inputs ---------- */
.stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"], .stApp [data-baseweb="textarea"],
.stApp [data-testid="stTextInputRootElement"], .stApp [data-testid="stNumberInputContainer"] {
  background: var(--surface) !important; border-color: var(--border) !important; border-radius: 8px;
}
.stApp [data-testid="stNumberInputContainer"] [data-baseweb="input"],
.stApp [data-testid="stNumberInputContainer"] [data-baseweb="base-input"] { border-color: transparent !important; }
.stApp input, .stApp textarea {
  color: var(--text-primary) !important; -webkit-text-fill-color: var(--text-primary) !important;
  background: transparent !important; caret-color: var(--text-primary);
}
.stApp input::placeholder, .stApp textarea::placeholder {
  color: var(--text-secondary) !important; -webkit-text-fill-color: var(--text-secondary) !important; opacity: 1;
}
.stApp [data-baseweb="input"]:focus-within, .stApp [data-testid="stNumberInputContainer"]:focus-within {
  border-color: var(--focus-ring) !important; outline: 1px solid var(--focus-ring);
}
.stApp [data-testid="stNumberInputStepDown"], .stApp [data-testid="stNumberInputStepUp"] {
  background: var(--surface-subtle) !important; color: var(--text-primary) !important; border: 0 !important;
}
.stApp [data-testid="stNumberInputStepDown"]:hover:not(:disabled),
.stApp [data-testid="stNumberInputStepUp"]:hover:not(:disabled) { background: var(--primary-soft) !important; color: var(--on-primary-soft) !important; }
.stApp [data-testid="stNumberInput"] input { text-align: right; font-variant-numeric: tabular-nums; }
.stApp [data-testid="InputInstructions"] { display: none; }

/* ---------- select menus & popovers ---------- */
.stApp [data-baseweb="select"] > div { background: var(--surface) !important; border-color: var(--border) !important; color: var(--text-primary) !important; }
[data-baseweb="popover"] > div, [data-baseweb="popover"] ul, [data-baseweb="menu"] {
  background: var(--surface) !important; color: var(--text-primary) !important; border-color: var(--border) !important;
}
[data-baseweb="popover"] li { color: var(--text-primary) !important; }
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] {
  background: var(--primary-soft) !important; color: var(--on-primary-soft) !important;
}
[data-baseweb="tooltip"] > div, [data-baseweb="tooltip"] [role="tooltip"] {
  background: var(--text-primary) !important; color: var(--background) !important;
}
.stApp [data-testid="stTooltipHoverTarget"], .stApp [data-testid="stTooltipHoverTarget"] *,
.stApp [data-testid="stTextInputRootElement"] button, .stApp [data-testid="stTextInputRootElement"] button * {
  color: var(--text-secondary) !important; opacity: 1 !important; background: transparent !important;
}
.stApp [data-testid="stTooltipHoverTarget"] svg, .stApp [data-testid="stTooltipHoverTarget"] svg *,
.stApp [data-testid="stTextInputRootElement"] svg, .stApp [data-testid="stTextInputRootElement"] svg * { stroke: var(--text-secondary) !important; }

/* ---------- react-aria selects, date and time pickers (Streamlit 1.5x+) ---------- */
.stApp .react-aria-ComboBox > div, .stApp [data-testid="stDateInputField"], .stApp [data-testid="stTimeInputField"],
.stApp [data-testid="stTimeInputTimeDisplay"] {
  background: var(--surface) !important; border-color: var(--border) !important; color: var(--text-primary) !important;
}
.stApp .react-aria-ComboBox *, .stApp [data-testid="stDateInputField"] *, .stApp [data-testid="stTimeInputField"] *,
.stApp [data-testid="stTimeInputTimeDisplay"] * { color: var(--text-primary); }
.stApp [data-testid="stTimeInputTimeDisplay"] [role="spinbutton"][aria-valuetext="Empty"],
.stApp [data-testid="stDateInputField"] [role="spinbutton"][aria-valuetext="Empty"] { color: var(--text-secondary) !important; }
.stApp [role="spinbutton"]:focus { background: var(--primary) !important; color: var(--on-primary) !important; border-radius: 4px; outline: none; }
.stApp .react-aria-ComboBox svg, .stApp [data-testid="stDateInputField"] svg, .stApp [data-testid="stTimeInputField"] svg { color: var(--text-secondary) !important; }
[data-testid="stSelectboxVirtualDropdown"], [data-testid="stDateInputCalendar"], [data-testid="stTimeInputDropdown"] {
  background: var(--surface) !important; color: var(--text-primary) !important; border: 1px solid var(--border) !important;
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"], [data-testid="stTimeInputDropdown"] [role="option"] { color: var(--text-primary) !important; background: transparent !important; }
[data-testid="stSelectboxVirtualDropdown"] [role="option"][data-hovered], [data-testid="stSelectboxVirtualDropdown"] [role="option"][data-focused],
[data-testid="stTimeInputDropdown"] [role="option"][data-hovered], [data-testid="stTimeInputDropdown"] [role="option"][data-focused] {
  background: var(--surface-subtle) !important;
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"], [data-testid="stTimeInputDropdown"] [role="option"][aria-selected="true"] {
  background: var(--primary-soft) !important; color: var(--on-primary-soft) !important; font-weight: 600;
}
[data-testid="stDateInputCalendar"] *, [data-testid="stDateInputCalendar"] button { color: var(--text-primary) !important; }
[data-testid="stDateInputCalendar"] [data-outside-month], [data-testid="stDateInputCalendar"] [data-disabled] { color: var(--text-secondary) !important; }
[data-testid="stDateInputCalendar"] [data-hovered] { background: var(--surface-subtle) !important; }
[data-testid="stDateInputCalendar"] [data-selected], [data-testid="stDateInputCalendar"] [aria-selected="true"] > * {
  background: var(--primary) !important; color: var(--on-primary) !important;
}
[data-testid="stDateInputCalendar"] select { background: var(--surface) !important; color: var(--text-primary) !important; }

/* ---------- buttons ---------- */
.stApp button[data-testid="stBaseButton-primary"] {
  background: var(--primary) !important; color: var(--on-primary) !important; border: 1px solid var(--primary) !important;
  min-height: 44px; border-radius: 8px; font-weight: 600;
}
.stApp button[data-testid="stBaseButton-primary"] * { color: var(--on-primary) !important; }
.stApp button[data-testid="stBaseButton-primary"]:hover:not(:disabled) {
  background: var(--primary-hover) !important; border-color: var(--primary-hover) !important;
}
.stApp button[data-testid="stBaseButton-secondary"], .stApp button[data-testid="stBaseButton-secondaryFormSubmit"],
.stApp a[data-testid="stBaseLinkButton-secondary"] {
  background: var(--surface) !important; color: var(--text-primary) !important; border: 1px solid var(--border) !important;
  min-height: 44px; border-radius: 8px;
}
.stApp button[data-testid="stBaseButton-secondary"] *, .stApp button[data-testid="stBaseButton-secondaryFormSubmit"] *,
.stApp a[data-testid="stBaseLinkButton-secondary"] * { color: inherit !important; }
.stApp button[data-testid="stBaseButton-secondary"]:hover:not(:disabled),
.stApp button[data-testid="stBaseButton-secondaryFormSubmit"]:hover:not(:disabled) {
  background: var(--surface-subtle) !important; border-color: var(--primary) !important; color: var(--text-primary) !important;
}
.stApp button[data-testid="stBaseButton-tertiary"] { color: var(--primary) !important; min-height: 44px; }
.stApp button[data-testid="stBaseButton-tertiary"] * { color: inherit !important; }
.stApp button[data-testid="stBaseButton-tertiary"]:hover:not(:disabled) { color: var(--primary-hover) !important; text-decoration: underline; }
.stApp button:disabled, .stApp button:disabled:hover {
  background: var(--surface-subtle) !important; color: var(--text-secondary) !important;
  border-color: var(--border) !important; cursor: not-allowed;
}
.stApp button:disabled * { color: var(--text-secondary) !important; }

/* ---------- segmented controls (role=radio) & pills (aria-pressed) ---------- */
.stApp [data-testid="stButtonGroup"] button[role="radio"], .stApp [data-testid="stButtonGroup"] button[aria-pressed] {
  background: var(--surface) !important; color: var(--text-primary) !important; border-color: var(--border) !important; min-height: 40px;
}
.stApp [data-testid="stButtonGroup"] button[aria-pressed] { border-radius: 999px !important; }
.stApp [data-testid="stButtonGroup"] button[role="radio"] *, .stApp [data-testid="stButtonGroup"] button[aria-pressed] * { color: inherit !important; }
.stApp [data-testid="stButtonGroup"] button[role="radio"]:hover, .stApp [data-testid="stButtonGroup"] button[aria-pressed]:hover {
  background: var(--surface-subtle) !important;
}
.stApp [data-testid="stButtonGroup"] button[aria-checked="true"], .stApp [data-testid="stButtonGroup"] button[aria-pressed="true"] {
  background: var(--primary-soft) !important; color: var(--on-primary-soft) !important;
  border-color: var(--primary) !important; font-weight: 600; position: relative; z-index: 1;
}

/* ---------- file uploader ---------- */
.stApp [data-testid="stFileUploaderDropzone"] {
  background: var(--surface) !important; border: 1px dashed var(--border) !important; border-radius: 12px; color: var(--text-primary);
}
.stApp [data-testid="stFileUploaderDropzone"] * { color: var(--text-secondary); }
.stApp [data-testid="stFileUploaderDropzone"] button { color: var(--text-primary) !important; }
.stApp [data-testid="stFileUploaderFile"], .stApp [data-testid="stFileUploaderFile"] * { color: var(--text-primary) !important; }
.stApp [data-testid="stFileUploaderDeleteBtn"] button { background: transparent !important; border: 0 !important; min-height: 32px; }

/* ---------- expanders, checkboxes, code ---------- */
.stApp [data-testid="stExpander"] details {
  background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 8px;
}
.stApp [data-testid="stExpander"] summary { background: var(--surface) !important; }
.stApp [data-testid="stExpander"] summary, .stApp [data-testid="stExpander"] summary * { color: var(--text-primary) !important; }
.stApp [data-testid="stExpanderDetails"] { background: var(--surface) !important; }
.stApp button[data-testid="stBaseButton-elementToolbar"] { background: var(--surface) !important; color: var(--text-primary) !important; border: 1px solid var(--border) !important; }
.stApp [data-testid="stExpander"] summary:hover, .stApp [data-testid="stExpander"] summary:hover * { color: var(--primary) !important; }
.stApp [data-baseweb="checkbox"] > span:first-of-type, .stApp [data-baseweb="checkbox"] [role="checkbox"] {
  border-color: var(--text-secondary) !important; background-color: var(--surface) !important;
}
.stApp [data-baseweb="checkbox"] input:checked + span, .stApp [data-baseweb="checkbox"] [aria-checked="true"] {
  background-color: var(--primary) !important; border-color: var(--primary) !important;
}
.stApp [data-testid="stCode"] pre, .stApp [data-testid="stCode"] code {
  background: var(--surface-subtle) !important; color: var(--text-primary) !important;
}
.stApp [data-testid="stSpinner"], .stApp [data-testid="stSpinner"] * { color: var(--text-secondary) !important; }
.stApp [data-testid="stImage"] img { filter: none !important; border-radius: 4px; }

/* ---------- app components (ui.py) ---------- */
.ss-brand { display: flex; align-items: center; gap: 12px; }
.ss-icon { display: inline-block; flex: none; -webkit-mask: var(--icon) center / contain no-repeat; mask: var(--icon) center / contain no-repeat; }
.ss-icon.pumpkin { width: 28px; height: 28px; background: var(--primary); --icon: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22black%22%20stroke-width%3D%221.6%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M12%207c-1.2-2-.4-3.6%201.2-4.2%22/%3E%3Cpath%20d%3D%22M12%207c-4.6-1.8-9%20.8-9%206s3.6%207.5%209%207.5%209-2.3%209-7.5-4.4-7.8-9-6z%22/%3E%3Cpath%20d%3D%22M12%207c-2%201.6-2.6%204-2.6%206.6s.6%205.2%202.6%206.9%22/%3E%3Cpath%20d%3D%22M12%207c2%201.6%202.6%204%202.6%206.6s-.6%205.2-2.6%206.9%22/%3E%3C/svg%3E"); }
.ss-icon.ghost { width: 24px; height: 24px; background: var(--text-secondary); --icon: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22black%22%20stroke-width%3D%221.6%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M5%2020V11a7%207%200%200%201%2014%200v9l-2.3-1.6L14.3%2020%2012%2018.4%209.7%2020l-2.4-1.6z%22/%3E%3Cpath%20d%3D%22M9.5%2011h.01M14.5%2011h.01%22/%3E%3C/svg%3E"); }
.ss-name { font-size: 20px; line-height: 28px; font-weight: 700; color: var(--text-primary); margin: 0; }
.ss-tagline { font-size: 14px; line-height: 20px; color: var(--text-secondary); }
.ss-label { display: inline-block; font-size: 12px; line-height: 18px; padding: 2px 8px; border-radius: 6px;
  background: var(--surface-subtle); color: var(--text-secondary); border: 1px solid var(--border); margin-left: 8px; }
.ss-title { font-size: 30px; line-height: 38px; font-weight: 700; color: var(--text-primary); margin: 0 0 8px; }
.ss-desc { font-size: 16px; line-height: 24px; color: var(--text-secondary); margin: 0 0 24px; }
.ss-h2 { font-size: 20px; line-height: 28px; font-weight: 600; color: var(--text-primary); margin: 0 0 4px; }
.ss-h3 { font-size: 16px; line-height: 24px; font-weight: 600; color: var(--text-primary); margin: 16px 0 8px; }
.ss-support { font-size: 14px; line-height: 20px; color: var(--text-secondary); margin: 0 0 16px; }

.ss-steps { display: flex; gap: 8px; list-style: none; padding: 0 !important; margin: 0 0 32px !important; flex-wrap: wrap; }
.ss-step { margin: 0 !important; }
.ss-step { display: flex; align-items: center; gap: 8px; font-size: 14px; line-height: 20px; color: var(--text-secondary);
  padding: 6px 12px 6px 6px; border-radius: 999px; border: 1px solid var(--border); background: var(--surface); }
.ss-step-num { width: 24px; height: 24px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600; background: var(--surface-subtle); color: var(--text-secondary); }
.ss-step.current { border-color: var(--primary); color: var(--on-primary-soft); background: var(--primary-soft); font-weight: 600; }
.ss-step.current .ss-step-num { background: var(--primary); color: var(--on-primary); }
.ss-step.done { color: var(--text-primary); }
.ss-step.done .ss-step-num { background: var(--success-background); color: var(--success-text); }

.ss-notice { display: flex; gap: 8px; font-size: 14px; line-height: 20px; padding: 12px 16px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--surface-subtle); color: var(--text-primary); margin: 8px 0 16px; }
.ss-notice b { font-weight: 600; }
.ss-notice.success { background: var(--success-background); color: var(--success-text); border-color: transparent; }
.ss-notice.warning { background: var(--warning-background); color: var(--warning-text); border-color: transparent; }
.ss-notice.error { background: var(--error-background); color: var(--error-text); border-color: transparent; }

.ss-badge { display: inline-block; font-size: 12px; line-height: 18px; font-weight: 600; padding: 2px 8px; border-radius: 6px;
  background: var(--primary-soft); color: var(--on-primary-soft); }
.ss-badge.neutral { background: var(--surface-subtle); color: var(--text-secondary); }
.ss-merchant { font-size: 16px; line-height: 24px; font-weight: 600; color: var(--text-primary); margin: 8px 0 4px; }

.ss-recon { width: 100%; border-collapse: collapse; font-size: 14px; line-height: 20px; margin: 8px 0; }
.ss-recon td { padding: 6px 0; color: var(--text-secondary); border-bottom: 1px solid var(--border); }
.ss-recon td.money { color: var(--text-primary); }
.ss-recon tr.total td { color: var(--text-primary); font-weight: 600; }
.ss-recon tr:last-child td { border-bottom: 0; }
.money { font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap; }

.ss-people { width: 100%; border-collapse: collapse; margin: 8px 0 16px; }
.ss-people th { font-size: 12px; line-height: 18px; font-weight: 600; color: var(--text-secondary); text-align: left;
  padding: 0 0 8px; border-bottom: 1px solid var(--border); }
.ss-people th.money { text-align: right; }
.ss-people td { padding: 12px 0; border-bottom: 1px solid var(--border); font-size: 16px; line-height: 24px; color: var(--text-primary); vertical-align: top; }
.ss-people td.money { font-weight: 600; }
.ss-people .detail { display: block; font-size: 14px; line-height: 20px; color: var(--text-secondary); font-weight: 400; }
.ss-person { display: flex; align-items: center; gap: 12px; min-width: 0; }
.ss-avatar { width: 32px; height: 32px; border-radius: 50%; flex: none; display: inline-flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600; background: var(--surface-subtle); color: var(--text-primary); border: 1px solid var(--border); }
.ss-person-name { overflow-wrap: anywhere; }
.ss-amount { font-size: 32px; line-height: 40px; font-weight: 700; color: var(--text-primary); font-variant-numeric: tabular-nums; }
.ss-amount-label { font-size: 14px; line-height: 20px; color: var(--text-secondary); }
.ss-empty { display: flex; gap: 12px; align-items: center; padding: 16px; border: 1px dashed var(--border); border-radius: 8px;
  color: var(--text-secondary); font-size: 14px; line-height: 20px; }

.ss-copy-row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.ss-copy-btn { min-height: 44px; padding: 10px 18px; border: 0; border-radius: 8px; background: var(--primary);
  color: var(--on-primary); font: inherit; font-weight: 600; cursor: pointer; }
.ss-copy-btn:hover { background: var(--primary-hover); }
.ss-copy-btn:focus-visible { outline: 2px solid var(--focus-ring); outline-offset: 3px; }
.ss-copy-status { font-size: 14px; line-height: 20px; color: var(--text-secondary); }

@media (prefers-reduced-motion: reduce) { .stApp * { transition: none !important; animation: none !important; } }
@media (max-width: 640px) {
  .block-container { padding: 0 16px 48px !important; }
  [class*="st-key-panel_"] { padding: 16px; }
  .ss-title { font-size: 26px; line-height: 34px; }
  .ss-label { display: none; }
}
"""


def css(mode: str) -> str:
    """Full stylesheet for the chosen mode ("light", "dark" or "system")."""
    if mode not in MODES:
        mode = "system"
    return f"<style>\n{token_block(mode)}\n{_COMPONENTS}\n</style>"


def persistence_script(mode: str) -> str:
    """Remember the theme in localStorage and restore it on the next visit.

    On a fresh page load with no ?theme= in the URL, a saved explicit choice is
    restored by reloading once with ?theme=Light or ?theme=Dark (the theme control
    is bound to that query parameter). This only happens before the
    user has entered anything, because Streamlit starts a new session on reload.
    """
    if mode not in MODES:
        mode = "system"
    return f"""<script>
(function () {{
  var KEY = "{STORAGE_KEY}", mode = "{mode}";
  var LABELS = {{ light: "Light", dark: "Dark", system: "System" }};
  var url = new URL(window.location.href);
  var saved = null;
  try {{ saved = window.localStorage.getItem(KEY); }} catch (e) {{}}
  var firstRun = !window.__summonThemeReady;
  window.__summonThemeReady = true;
  if (firstRun && !url.searchParams.get("theme") && (saved === "light" || saved === "dark") && saved !== mode) {{
    url.searchParams.set("theme", LABELS[saved]);
    window.location.replace(url.toString());
    return;
  }}
  try {{ window.localStorage.setItem(KEY, mode); }} catch (e) {{}}
  document.documentElement.setAttribute("data-theme", mode);
}})();
</script>"""
