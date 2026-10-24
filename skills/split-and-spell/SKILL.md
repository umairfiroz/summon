---
name: split-and-spell
description: Splits a restaurant or shop receipt between friends to the exact penny and produces a reconciled, copy-pasteable summary. Use when the user shares a receipt photo or bill and asks who owes what, wants to split a bill by item or equally, divide a tab, or share a service charge or tip fairly.
license: MIT
compatibility: Needs a vision-capable model to read receipt photos (built and tested with the open-weight Gemma 4) and Python 3.9+ to run scripts/split_bill.py. No third-party packages.
metadata:
  author: umairfiroz
  version: "1.0"
  source: https://github.com/umairfiroz/hacktoberfest26
---

# Split & Spell

Turn a receipt into an exact, reconciled split.
Never do the money maths yourself: always run `scripts/split_bill.py`, which works in
whole pence and guarantees the shares add up to the bill.

## Steps

1. **Read the receipt.** Look at the image and list every printed line item with its
   final line price (already multiplied by quantity). Also note any service charge,
   tip, whole-bill discount, tax *added on top* and the printed total.
   UK VAT that is "included" is not added on top, so leave `tax_added` out.
2. **Get the people.** Ask who was there and who paid, if the user hasn't said.
3. **Assign items.** Ask who shared what. Items with no `shared_by` are split between
   everyone. Show the user the item list and let them correct misreadings.
4. **Write the bill JSON** in the format in [references/receipt-schema.md](references/receipt-schema.md)
   and save it, e.g. as `bill.json`.
5. **Run the calculator:**

   ```bash
   python scripts/split_bill.py bill.json
   ```

6. **Check the result.** If `matches_printed_total` is `false`, tell the user the
   difference and ask them to check the items before going on.
7. **Report** each person's total and what they owe the payer, using the exact amount
   strings from the script output.
8. **Write the summary.** One line per person (`Name: £amount`), then
   `Total assigned: £…`, which must equal the bill total. Don't say anyone has paid:
   the split doesn't verify payments.

## Example

Input `bill.json`:

```json
{
  "people": ["Umair", "Ali", "Sara"],
  "payer": "Umair",
  "currency_symbol": "£",
  "items": [
    {"name": "Zombie Burger", "line_total": 13.50, "shared_by": ["Ali"]},
    {"name": "Graveyard Nachos", "line_total": 8.95}
  ],
  "service_charge": 2.80,
  "total": 25.25
}
```

Output (abridged): `"debts": {"Ali": "£18.54", "Sara": "£3.35"}`, `"matches_printed_total": true`.

Example summary:

```
Ali: £18.54
Sara: £3.35
Umair: £3.36
Total assigned: £25.25
```

## Edge cases

- Discount lines printed against an item: include them as items with a negative `line_total`.
- Someone ordered nothing: they owe nothing and receive no share of extras.
- If every person has a zero subtotal, extras are split evenly.
- Duplicate names are merged; names are case-sensitive in `shared_by`, so match `people` exactly.
- If the script prints `error: ...` it exits with code 1. Fix the JSON and run it again.
