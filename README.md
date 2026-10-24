# Split & Spell

**Receipts in. Fair shares out.**

Split & Spell fuses two tools people already use, a receipt scanner and a bill-splitting calculator, into one workflow. You take a photo of the bill, and the open-weight **Gemma 4** model reads the items. You check them, choose how to split, and get amounts that add up to the bill to the penny.

Built solo at **Hacktoberfest Southampton 2026** (theme: *Fusion*).

## What it does

1. **Upload.** Upload a receipt photo (JPG, PNG or WEBP, up to 10 MB), use the labelled sample receipt, or enter items by hand.
2. **Review.** Gemma 4 extracts the items, line totals, charges and printed total, and you can correct any line. The app shows the items total and the detected receipt total separately, and if they don't match it asks you to confirm before going on. It never changes numbers to force a match.
3. **Split.** Add participants, then choose:
   - **Equal split.** Remainder pennies are shown, not hidden: £10.00 between three people is £3.34, £3.33, £3.33.
   - **Custom amounts.** A running remainder shows "£8.00 left to assign" or "£3.00 over the bill total", and Confirm stays blocked until everything balances.
   - **By item.** Tap who had each item. Shared items are divided equally, and charges or discounts are shared in proportion to what each person had.
4. **Result.** Each person's amount, "Total assigned", and a **Copy summary** button.

The app has **Light, Dark and System** themes. The choice is saved in your browser, and switching never resets your data.

## How the AI is used

| Step | Model | Input → output |
|---|---|---|
| Read the receipt | Gemma 4 (`gemma-4-26b-a4b-it` by default) | Receipt image + extraction prompt → JSON with items, line totals, service charge, tip, discounts and printed total |

The model never does the money maths. All arithmetic is in [`split_and_spell/split.py`](split_and_spell/split.py), in whole pence with exact fractions, so a model mistake can't change what anyone owes. Gemma's output is validated, shown in full under "What Gemma 4 extracted", and can be corrected before splitting.

**Privacy:** an uploaded receipt is sent to Google's Gemini API to be read. The app doesn't store receipts, and only the theme choice is saved in the browser.

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
| [Pillow](https://github.com/python-pillow/Pillow) | Fixing photo rotation and size | MIT-CMU |
| [pytest](https://github.com/pytest-dev/pytest) (dev only) | Tests | MIT |
| Inter font, self-hosted in `static/fonts` via [Fontsource](https://fontsource.org) | Typography that works offline | SIL Open Font License 1.1 |

## Run it

You need Python 3.10+ and, to read real receipts, a free Gemini API key.

```bash
git clone https://github.com/umairfiroz/hacktoberfest26.git
cd hacktoberfest26
python -m venv .venv
# Windows:  .venv\Scripts\Activate.ps1      macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

Set your key (or paste it into the app):

```bash
# Windows PowerShell
setx GEMINI_API_KEY "your-key"        # then open a new terminal
# macOS/Linux
export GEMINI_API_KEY="your-key"
```

```bash
streamlit run app.py
```

### Try it in 30 seconds

Click **Use sample receipt** (The Lantern Kitchen, £56.00, four people), then **Continue to split**, and switch between Equal (£14.00 each), Custom and By item (£17 / £19 / £12 / £8). The sample is preloaded and labelled as such. Click **Read this sample with Gemma 4**, or upload your own photo, to see live extraction.

## Use it as an agent skill

[`skills/split-and-spell`](skills/split-and-spell) follows the [Agent Skills open standard](https://agentskills.io/specification) and passes the `skills-ref` validator. The agent reads the receipt with its own vision model and runs a standard-library-only calculator for exact amounts:

```bash
python skills/split-and-spell/scripts/split_bill.py bill.json
```

## Tests

```bash
pip install pytest
python -m pytest
```

The tests cover the £56.00 sample in all three split modes, £10.00 divided between three people, 500 random bills that must reconcile to the penny, custom-amount remainders, receipt-total mismatch, manual entry, blank names, extraction and network failures, switching themes without losing edits, and the full workflow through the real Streamlit UI with the model mocked.

## Project structure

```
app.py                         Streamlit app: upload → review → split → result
split_and_spell/gemma.py       Gemma 4 receipt reading, retries, validation
split_and_spell/split.py       Exact money maths (no AI, no UI)
split_and_spell/theme.py       Design tokens, Light/Dark/System styles, theme persistence
split_and_spell/ui.py          Small accessible HTML components
split_and_spell/sample.py      Labelled demo fixture
DESIGN.md                      Design specification
skills/split-and-spell/        Agent Skill version
tests/                         pytest suite
```
