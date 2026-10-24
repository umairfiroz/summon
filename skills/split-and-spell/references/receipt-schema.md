# Bill JSON format for `scripts/split_bill.py`

```json
{
  "people": ["Umair", "Ali", "Sara"],
  "payer": "Umair",
  "currency_symbol": "£",
  "items": [
    {"name": "Pumpkin Spice Latte x2", "line_total": 7.80, "shared_by": ["Umair", "Sara"]},
    {"name": "Graveyard Nachos", "line_total": 8.95},
    {"name": "Promo: 2-for-1", "line_total": -2.50, "shared_by": ["Ali"]}
  ],
  "tax_added": 0,
  "service_charge": 2.80,
  "tip": 0,
  "discount": 0,
  "total": 17.05
}
```

| Field | Required | Meaning |
|---|---|---|
| `people` | yes | Everyone splitting the bill. |
| `payer` | yes | Who paid. Must be one of `people`. |
| `currency_symbol` | no | Used when formatting output. Default `£`. |
| `items[].name` | no | Item name as printed. |
| `items[].line_total` | yes | Final price for that line (quantity already applied). Negative for item discounts. |
| `items[].shared_by` | no | Who shared the item (split equally). Default: everyone. |
| `tax_added` | no | Tax added on top of prices only (not included VAT). |
| `service_charge`, `tip` | no | Shared in proportion to each person's item total. |
| `discount` | no | Whole-bill discount as a positive number, shared proportionally. |
| `total` | no | Printed total, used to check the maths (`matches_printed_total`). |

Amounts may be numbers or strings (`"7.80"`). Output amounts are formatted strings
such as `"£12.05"`, and every person's `total` adds up to `grand_total` exactly.
