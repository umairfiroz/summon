#!/usr/bin/env python3
"""Split & Spell bill calculator (self-contained, standard library only).

Usage:  python split_bill.py bill.json      or      cat bill.json | python split_bill.py

See references/receipt-schema.md for the input format. Prints a JSON result.
"""


from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from fractions import Fraction
import math


def to_pence(value) -> int:
    """Convert a money value (str, int, float, Decimal, None) to integer pence."""
    if value is None or value == "":
        return 0
    try:
        amount = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Not a valid amount: {value!r}") from exc
    if not amount.is_finite():
        raise ValueError(f"Not a valid amount: {value!r}")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def format_money(pence: int, symbol: str = "£") -> str:
    """Format integer pence as e.g. '£12.05' or '-£1.50'."""
    sign = "-" if pence < 0 else ""
    pence = abs(pence)
    return f"{sign}{symbol}{pence // 100}.{pence % 100:02d}"


def split_evenly(total: int, people: list[str]) -> dict[str, int]:
    """Split integer pence equally; leftover pennies go to the first people."""
    if not people:
        raise ValueError("Cannot split between zero people.")
    base, remainder = divmod(total, len(people))
    return {p: base + (1 if i < remainder else 0) for i, p in enumerate(people)}


def allocate_proportionally(total: int, weights: dict[str, int]) -> dict[str, int]:
    """Share `total` pence in proportion to non-negative `weights`.

    Uses the largest-remainder method so the result sums to `total` exactly.
    Works for negative totals (discounts). If every weight is zero the total
    is split evenly instead.
    """
    names = list(weights)
    if not names:
        raise ValueError("Cannot allocate between zero people.")
    if total == 0:
        return {n: 0 for n in names}

    sign = -1 if total < 0 else 1
    magnitude = abs(total)
    clipped = {n: max(0, weights[n]) for n in names}
    weight_sum = sum(clipped.values())
    if weight_sum == 0:
        return {n: sign * v for n, v in split_evenly(magnitude, names).items()}

    shares: dict[str, int] = {}
    remainders: list[tuple[int, int, str]] = []
    for index, name in enumerate(names):
        quotient, remainder = divmod(magnitude * clipped[name], weight_sum)
        shares[name] = quotient
        # Sort key: biggest remainder first, then original order for ties.
        remainders.append((-remainder, index, name))

    leftover = magnitude - sum(shares.values())
    for _, _, name in sorted(remainders)[:leftover]:
        shares[name] += 1

    return {n: sign * shares[n] for n in names}


@dataclass
class Item:
    name: str
    price: int  # line total in pence (can be negative for a discount line)
    shared_by: list[str]


@dataclass
class PersonShare:
    name: str
    items_total: int = 0
    extras_total: int = 0
    items: list[tuple[str, int]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.items_total + self.extras_total


@dataclass
class SplitResult:
    people: dict[str, PersonShare]
    payer: str
    grand_total: int
    unassigned: list[str]

    def debts(self) -> dict[str, int]:
        """Amount each non-payer owes the payer (only positive amounts)."""
        return {
            name: share.total
            for name, share in self.people.items()
            if name != self.payer and share.total > 0
        }


def split_bill(
    items: list[Item],
    people: list[str],
    payer: str,
    extras: int = 0,
) -> SplitResult:
    """Work out each person's share.

    `extras` is the net of tax-on-top + service + tip - discounts, in pence.
    Items with nobody assigned are reported in `unassigned` and left out.

    Each person's exact share is computed with fractions first, then rounded
    to whole pence once (largest-remainder), so people who shared everything
    pay exactly the same and the totals always add up to the bill.
    """
    people = _clean_people(people)
    if payer not in people:
        raise ValueError(f"Payer {payer!r} is not one of the people.")

    shares = {p: PersonShare(name=p) for p in people}
    exact_items = {p: Fraction(0) for p in people}
    unassigned: list[str] = []
    assigned_total = 0

    for item in items:
        sharers = [p for p in people if p in item.shared_by]
        if not sharers:
            unassigned.append(item.name)
            continue
        assigned_total += item.price
        for person in sharers:
            exact_items[person] += Fraction(item.price, len(sharers))
        # Rounded per-item amounts, only for display. Leftover pennies go to
        # whoever has the lowest running total.
        sharers.sort(key=lambda p: shares[p].items_total)
        for person, amount in split_evenly(item.price, sharers).items():
            shares[person].items_total += amount
            shares[person].items.append((item.name, amount))

    # Exact extras share, proportional to (non-negative) exact item totals.
    weights = {p: max(Fraction(0), exact_items[p]) for p in people}
    weight_sum = sum(weights.values())
    exact_totals = {}
    for person in people:
        if weight_sum > 0:
            extra = Fraction(extras) * weights[person] / weight_sum
        else:
            extra = Fraction(extras, len(people))
        exact_totals[person] = exact_items[person] + extra

    grand_total = assigned_total + extras
    rounded = _round_preserving_sum(exact_totals, grand_total)
    for person in people:
        # Extras line = whatever makes the displayed lines add up to the total.
        shares[person].extras_total = rounded[person] - shares[person].items_total

    return SplitResult(
        people=shares, payer=payer, grand_total=grand_total, unassigned=unassigned
    )


def _round_preserving_sum(exact: dict[str, Fraction], target: int) -> dict[str, int]:
    """Round exact amounts to integers that sum to `target` (largest remainder)."""
    floors = {n: math.floor(v) for n, v in exact.items()}
    leftover = target - sum(floors.values())
    order = sorted(
        enumerate(exact),
        key=lambda pair: (-(exact[pair[1]] - floors[pair[1]]), pair[0]),
    )
    for _, name in order[:leftover]:
        floors[name] += 1
    return floors


def _clean_people(people: list[str]) -> list[str]:
    cleaned: list[str] = []
    for person in people:
        name = person.strip()
        if name and name not in cleaned:
            cleaned.append(name)
    if not cleaned:
        raise ValueError("Add at least one person.")
    return cleaned


def parse_people(text: str) -> list[str]:
    """Turn 'Umair, Ali,  Sara, ali' into ['Umair', 'Ali', 'Sara'] (case-insensitive dedupe)."""
    seen: set[str] = set()
    result: list[str] = []
    for raw in text.replace("\n", ",").split(","):
        name = raw.strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            result.append(name)
    return result


# --------------------------------------------------------------------------- #
# Equal and custom splits
# --------------------------------------------------------------------------- #

def equal_split(total: int, people: list[str]) -> dict[str, int]:
    """Divide the whole bill equally.

    Remainder pennies go one each to the first people in the list, so
    £10.00 between three people is £3.34, £3.33, £3.33.
    """
    return split_evenly(total, _clean_people(people))


@dataclass
class CustomCheck:
    assigned: int
    remaining: int  # positive: still to assign; negative: over the bill

    @property
    def balanced(self) -> bool:
        return self.remaining == 0


def check_custom(total: int, amounts: dict[str, int]) -> CustomCheck:
    """Compare custom per-person amounts (pence) against the bill total."""
    if any(value < 0 for value in amounts.values()):
        raise ValueError("Amounts can't be negative.")
    assigned = sum(amounts.values())
    return CustomCheck(assigned=assigned, remaining=total - assigned)


# --------------------------------------------------------------------------- #
# Command-line interface for agents
# --------------------------------------------------------------------------- #

def run(bill: dict) -> dict:
    """Compute a split from the bill JSON described in references/receipt-schema.md."""
    people = bill.get("people") or []
    payer = bill.get("payer")
    symbol = bill.get("currency_symbol", "£")
    if not people:
        raise ValueError("'people' must be a non-empty list of names.")
    if not payer:
        raise ValueError("'payer' is required.")

    items = []
    for i, raw in enumerate(bill.get("items") or []):
        if "line_total" not in raw:
            raise ValueError(f"items[{i}] is missing 'line_total'.")
        shared_by = raw.get("shared_by") or people  # default: everyone shared it
        items.append(Item(name=str(raw.get("name", f"Item {i + 1}")), price=to_pence(raw["line_total"]), shared_by=list(shared_by)))

    extras = (
        to_pence(bill.get("tax_added")) + to_pence(bill.get("service_charge"))
        + to_pence(bill.get("tip")) - to_pence(bill.get("discount"))
    )
    result = split_bill(items, people, payer, extras=extras)

    out = {
        "payer": result.payer,
        "grand_total": format_money(result.grand_total, symbol),
        "unassigned_items": result.unassigned,
        "people": {},
        "debts": {name: format_money(p, symbol) for name, p in result.debts().items()},
    }
    if bill.get("total") is not None:
        printed = to_pence(bill["total"])
        out["matches_printed_total"] = printed == result.grand_total
        out["difference_from_printed_total"] = format_money(result.grand_total - printed, symbol)
    for name, share in result.people.items():
        out["people"][name] = {
            "items": [{"name": n, "amount": format_money(a, symbol)} for n, a in share.items],
            "extras": format_money(share.extras_total, symbol),
            "total": format_money(share.total, symbol),
        }
    return out


def main(argv: list[str]) -> int:
    import json
    import sys

    try:
        if len(argv) > 1:
            with open(argv[1], encoding="utf-8") as fh:
                bill = json.load(fh)
        else:
            bill = json.load(sys.stdin)
        print(json.dumps(run(bill), indent=2, ensure_ascii=False))
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv))
