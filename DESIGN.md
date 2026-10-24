# DESIGN.md — Split & Spell

## 1. Product and scope

Split & Spell combines receipt scanning with a shared bill-splitting calculator.
Hackathon theme: Fusion — connecting two existing tools into one useful workflow.

Tagline: "Receipts in. Fair shares out."

Core flow:
1. Upload a receipt or enter items manually.
2. Review and correct extracted items and prices.
3. Add participants.
4. Split equally, assign custom amounts, or allocate individual items.
5. Review and copy a reconciled summary.

Do not add chat, dashboards, payment integrations, or unrelated features without approval.
Only expose features that actually work. Label sample data honestly.

## 2. Visual direction

Use the approved light and dark Split & Spell mockups as visual references.
The product must feel practical, calm, friendly, and slightly autumnal.
Halloween is a restrained accent, not the main purpose of the interface.

Allowed:
- One small pumpkin outline next to the product name.
- At most one subtle ghost outline in a secondary or empty-state area.
- Warm neutral surfaces and burnt-orange accents.

Avoid:
- Neon, gradients, glow, glassmorphism, pure-black backgrounds.
- Horror typography, blood effects, floating particles, animated ghosts.
- Oversized marketing headings, decorative statistics, excessive cards.
- Emoji navigation or unclear labels such as "Cast the spell".

Use clear labels: "Total", "Amount owed", "Confirm split".

## 3. Theme modes

Provide Light, Dark, and System options through a clearly labelled theme control
in the header. A compact three-option menu is preferred; do not use an ambiguous
icon-only switch when three modes are available.

- Default on first visit: System.
- System follows the operating-system colour preference.
- Explicit Light or Dark overrides the system preference.
- Persist only the selected theme locally under `split-and-spell-theme`.
- Apply the resolved theme before first paint where the framework permits it.
- Update System mode when the operating-system preference changes.
- Changing theme must not reset the receipt, participants, allocation, or edits.
- Keyboard users must be able to open and operate the control.
- Indicate the selected mode in text and with a selected state.
- Do not invert or recolour uploaded receipt images.

The uploaded receipt remains its original colour. In the sample mockup this
means light paper inside a charcoal preview area, even in dark mode.

## 4. Semantic colour tokens

All components must use semantic tokens. Do not hard-code light colours inside
components or assume that text on a primary button is always white.

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

Validate contrast in the actual interface, including hover, selected, focus,
disabled, error, and placeholder states. Token values are design choices, not
proof of accessibility. Do not communicate status through colour alone.

For HTML/CSS frontends, use this reference implementation:

```css
:root,
[data-theme="light"] {
  color-scheme: light;
  --background: #F7F5EF;
  --surface: #FFFFFF;
  --surface-subtle: #F0EDE5;
  --text-primary: #222320;
  --text-secondary: #62645C;
  --border: #DEDCD3;
  --primary: #B84E19;
  --primary-hover: #993E12;
  --on-primary: #FFFFFF;
  --primary-soft: #F9E9DE;
  --on-primary-soft: #913B12;
  --success-text: #3E624B;
  --success-background: #EDF3EC;
  --warning-text: #775118;
  --warning-background: #FFF3DB;
  --error-text: #A12D2D;
  --error-background: #FBEDED;
  --focus-ring: #B84E19;
}

[data-theme="dark"] {
  color-scheme: dark;
  --background: #1C1D1B;
  --surface: #252622;
  --surface-subtle: #2D2E29;
  --text-primary: #F3F1E9;
  --text-secondary: #B9BCAF;
  --border: #45473F;
  --primary: #F0A06A;
  --primary-hover: #F5B58A;
  --on-primary: #1C1D1B;
  --primary-soft: #463023;
  --on-primary-soft: #F3B68D;
  --success-text: #B5D4BA;
  --success-background: #26372B;
  --warning-text: #F2CF8D;
  --warning-background: #3B3222;
  --error-text: #F1AEAE;
  --error-background: #41292A;
  --focus-ring: #F0A06A;
}

body {
  margin: 0;
  background: var(--background);
  color: var(--text-primary);
  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
}

.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
}

.button-primary {
  min-height: 44px;
  padding: 10px 18px;
  border: 0;
  border-radius: 8px;
  background: var(--primary);
  color: var(--on-primary);
  font: inherit;
  font-weight: 600;
}

.button-primary:hover:not(:disabled) {
  background: var(--primary-hover);
}

:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 3px;
}

.money {
  font-variant-numeric: tabular-nums;
  text-align: right;
}
```

Use the equivalent theme-token mechanism for non-HTML interfaces. Do not
introduce brittle CSS injection simply to copy this example literally.

## 5. Typography, spacing, and shape

Font: Inter with system-ui fallbacks. The app must work without remote fonts.

Type scale:
- Page title: 30px / 38px, weight 700.
- Section heading: 20px / 28px, weight 600.
- Component heading: 16px / 24px, weight 600.
- Body: 16px / 24px, weight 400.
- Supporting text: 14px / 20px.
- Small labels: 12px / 18px.
- Main amount: 32px / 40px, weight 700.

Use sentence case and left-aligned content. Right-align currency columns.
Use tabular numerals for money. Use monospace only for receipt-style text.

Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64px.
- Desktop page padding: 32px; mobile: 16px.
- Desktop panel padding: 24px; mobile: 16px.
- Major section gaps: 32px; related controls: 16px; labels: 8px.

Radii: panels 12px; inputs and buttons 8px; badges 6px; person chips pill-shaped.
Prefer thin borders over shadows. No default shadow on every card.

## 6. Application shell and layout

Header:
- Approximately 72px tall on desktop; may grow on small screens.
- Small pumpkin outline, product name, tagline.
- Optional "Fusion hackathon prototype" label.
- Theme control on the right.
- Thin bottom border; no unnecessary navigation.

Main content: centred, maximum width 1200px.

Page title: "Split your dinner receipt"
Description: "Check the items, choose a split, and see who owes what."

Progress: 1 Upload / 2 Review / 3 Split.
Show current and completed states clearly. Returning to a completed step must
preserve entered data.

Review screen desktop:
- Two columns with a 24px gap, aligned at the top.
- Approximately 38% receipt preview and 62% editing area, calculated after gap.
- Left: original receipt, merchant, review status, Replace receipt action.
- Right: items editor, reconciliation, split method, participants, summary,
  Confirm split action.

Mobile:
- Single column, with an optionally collapsible receipt preview.
- Stacked item rows where a table would become cramped.
- No horizontal page overflow or hover-only actions.
- Keep theme switching accessible without crowding the header.

## 7. Upload screen

Heading: "Start with your receipt"
Description: "Upload a clear photo or scanned receipt."

Use a restrained dashed upload area with a "Choose receipt" button.
Drag-and-drop is optional; it must not be the only upload method.
Show file types and size limits that match the actual implementation.

States: empty, selected, uploading, reading, complete, unsupported file, failed.
Loading text: "Reading your receipt…"
Failure: "We couldn't read this receipt. Try a clearer image or enter the items manually."

Provide manual entry. Do not invent progress percentages, extracted results,
or successful states. Distinguish a sample receipt from live extraction.

## 8. Review and correction

Heading: "Review receipt"
Description: "Check the items and prices before splitting."
Notice: "Check the total before continuing."

Editable fields:
- Item name.
- Quantity if implemented.
- Line total.
- Remove action.

Include Add item. Clearly distinguish unit prices from line totals.
Show calculated items total and detected receipt total separately.

Mismatch example:
"The items add up to £54.00, but the receipt total is £56.00."

Let the user correct missing items, discounts, or charges. Never silently alter
numbers to force reconciliation. Never invent OCR confidence percentages.
Highlight uncertain fields only when that information is genuinely available.

## 9. Participants and splitting

Participants: add, rename, remove. Use initials or simple neutral avatars.
Handle long names gracefully. Removing a person must not silently discard
allocations; require reassignment if needed.

Split selector: Equal split / Custom amounts / By item.
Only show implemented modes.

### Equal split

Divide the confirmed bill among participants.
Show total, participant count, per-person amounts, and penny adjustments.
Example: "£14.00 each" and "£56.00 split between 4 people".
If amounts differ by a penny, show actual allocations rather than a misleading
identical amount for everyone.

### Custom amounts

Provide an amount field per person and a running remainder.
Examples: "£8.00 left to assign", "£3.00 over the bill total",
"All £56.00 assigned".
Block confirmation until the assigned total matches the confirmed bill.

### By item

Assign each item to one or more people. Divide shared items among the selected
people. Make unassigned items and charges obvious. Block confirmation until
all amounts are allocated.

## 10. Money correctness

- Use Decimal or integer minor units, not binary floating-point money maths.
- Format GBP amounts to two decimal places.
- Do not mix currencies within a receipt.
- Reject negative values unless explicitly representing a discount.
- Participant amounts must sum exactly to the confirmed bill total.
- Allocate remainder pennies deterministically and show adjustments.

Example: £10.00 / 3 people = £3.34, £3.33, £3.33.

Show charges and discounts explicitly. State how shared charges are allocated.
Never add tax or service already included in the receipt. Require review when
receipt structure is ambiguous. Keep calculations separate from rendering.

## 11. Result screen

Heading: "Your split is ready"
Show merchant, confirmed total, method, people, individual amounts, and
"Total assigned: £56.00" or the applicable reconciled amount.

Actions:
- Copy summary, if implemented.
- Edit split.
- Start a new receipt.

Do not say Paid, Settled, or Payment complete: the app does not verify payments.
Copy feedback: "Summary copied". Surface clipboard failures with an alternative.

## 12. Components and interactions

Primary buttons: token-based background and foreground, at least 44px tall.
Secondary buttons: neutral outline or quiet surface with readable text.
Inputs: visible labels, inline errors, visible focus, preserved values on error.
Icons: one outline family, normally 18–20px; accessible names for icon buttons.

Use loading, success, failure, hover, focus, and disabled states consistently.
Explain blocked actions, e.g. "Assign the remaining £8.00 to continue."
Avoid decorative motion; respect reduced-motion preferences.
Never use whole-page inversion filters to implement dark mode.

## 13. Accessibility, privacy, and resilience

- Keyboard-operable upload, editor, split controls, theme picker, and result.
- Semantic headings and explicit form labels.
- Visible focus indicators and text explanations for errors.
- No colour-only meanings.
- Comfortable touch targets and usable zoomed layouts.
- Accessible announcements for asynchronous status changes.
- Original receipts remain readable in either theme.
- Explain if receipt processing sends the document to an external service.
- Do not log receipt contents unnecessarily or commit real personal receipts.
- Theme persistence must not automatically persist receipt data.

## 14. Demo fixture

Merchant: The Lantern Kitchen.

| Item | Amount |
|---|---:|
| Pumpkin pasta | £14.00 |
| Mushroom risotto | £16.00 |
| Margherita pizza | £12.00 |
| Garlic bread | £6.00 |
| Apple crumble | £8.00 |
| Total | £56.00 |

People: Umair, Maya, Sam, Alex.
Equal: £14.00 each.
Custom: Umair £18.00, Maya £16.00, Sam £12.00, Alex £10.00.
By item:
- Umair: pasta + half garlic bread = £17.00.
- Maya: risotto + half garlic bread = £19.00.
- Sam: pizza = £12.00.
- Alex: crumble = £8.00.

All examples reconcile to £56.00. Label preloaded content "Sample receipt".

## 15. Implementation instructions for Claude

Before changing code:
1. Read this file and inspect the existing Python/UI framework.
2. Identify reusable logic and components.
3. Describe the implementation plan briefly.
4. Preserve working extraction and allocation behaviour.
5. Implement small, testable changes without migrating frameworks unprompted.

Suggested components:
AppHeader, ThemeSelector, StepIndicator, ReceiptUploader, ReceiptPreview,
ReceiptItemsEditor, TotalReconciliation, ParticipantEditor,
SplitMethodSelector, EqualSplitPanel, CustomSplitPanel,
ItemAssignmentPanel, SplitSummary, StatusNotice.

Centralise tokens; keep extraction, monetary calculations, allocation, and UI
separate. Use the framework's supported styling approach. Prefer robust native
controls over brittle hacks.

If screenshots can be captured, compare both themes with the approved mockups.
Otherwise state which visual checks need manual verification.

## 16. Acceptance checklist

Visual:
- Warm ivory light mode and charcoal-grey dark mode match the references.
- Orange accents, subtle seasonal identity, consistent spacing and typography.
- No unreadable fields, bright leftover panels, or invisible icons in dark mode.
- Uploaded receipt image is unchanged in both themes.

Themes:
- Light, Dark, and System work.
- Selection persists across reloads.
- System preference changes are respected only in System mode.
- Theme switching preserves all bill data.
- No avoidable wrong-theme flash on startup.

Functional:
- Upload or manual entry works; extraction can be corrected.
- Split modes exposed in the UI actually work.
- Totals reconcile exactly, including remainder pennies.
- Errors have useful recovery actions; no dead controls.

Test cases:
- £56.00 sample in all implemented split modes.
- £10.00 divided between three people.
- Missing participant, blank name, invalid amount, unassigned item.
- Extraction failure and receipt-total mismatch.
- Long names, long item text, narrow phone layout, keyboard navigation.
- Full primary workflow in both light and dark themes.
