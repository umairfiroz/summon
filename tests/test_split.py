import importlib.util
import random
import sys
from pathlib import Path

import pytest

from split_and_spell import split as app_split

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("split_bill", ROOT / "skills/split-and-spell/scripts/split_bill.py")
skill_split = importlib.util.module_from_spec(_spec)
sys.modules["split_bill"] = skill_split
_spec.loader.exec_module(skill_split)

# The app module and the skill's self-contained script must behave identically.
MODULES = [app_split, skill_split]


@pytest.mark.parametrize("m", MODULES)
def test_to_pence(m):
    assert m.to_pence("7.80") == 780
    assert m.to_pence(0.1 + 0.2) == 30
    assert m.to_pence(2.675) == 268  # Decimal(str()) avoids the float 2.67499 trap
    assert m.to_pence(None) == 0
    assert m.to_pence("1,234.50") == 123450
    assert m.to_pence(-2.5) == -250
    with pytest.raises(ValueError):
        m.to_pence("abc")
    with pytest.raises(ValueError):
        m.to_pence(float("nan"))


@pytest.mark.parametrize("m", MODULES)
def test_format_money(m):
    assert m.format_money(1205) == "£12.05"
    assert m.format_money(5, "$") == "$0.05"
    assert m.format_money(-150) == "-£1.50"


@pytest.mark.parametrize("m", MODULES)
def test_split_evenly_pennies(m):
    assert m.split_evenly(1000, ["a", "b", "c"]) == {"a": 334, "b": 333, "c": 333}
    assert sum(m.split_evenly(-100, ["a", "b", "c"]).values()) == -100


@pytest.mark.parametrize("m", MODULES)
def test_allocate_proportionally_exact(m):
    shares = m.allocate_proportionally(799, {"a": 1000, "b": 2000, "c": 3395})
    assert sum(shares.values()) == 799
    assert m.allocate_proportionally(-300, {"a": 1, "b": 2}) == {"a": -100, "b": -200}
    assert m.allocate_proportionally(100, {"a": 0, "b": 0}) == {"a": 50, "b": 50}


@pytest.mark.parametrize("m", MODULES)
def test_sample_receipt_split(m):
    """The bundled sample receipt: 63.95 items + 7.99 service = 71.94."""
    people = ["Umair", "Ali", "Sara", "Zain"]
    items = [
        m.Item("Pumpkin Spice Latte x2", 780, ["Umair", "Sara"]),
        m.Item("Witch's Brew Mojito", 420, ["Ali"]),
        m.Item("Graveyard Nachos", 895, people),
        m.Item("Zombie Burger", 1350, ["Ali"]),
        m.Item("Vampire Wings", 1125, ["Zain"]),
        m.Item("Ghost Pepper Fries", 475, ["Zain", "Umair"]),
        m.Item("Coffin Brownie x2", 1100, ["Sara", "Ali"]),
        m.Item("Still Water", 250, ["Umair"]),
    ]
    result = m.split_bill(items, people, "Umair", extras=799)
    assert result.grand_total == 7194
    assert sum(p.total for p in result.people.values()) == 7194
    assert "Umair" not in result.debts()
    assert sum(result.debts().values()) == 7194 - result.people["Umair"].total


@pytest.mark.parametrize("m", MODULES)
def test_unassigned_and_zero_orders(m):
    items = [m.Item("Ghost item", 500, []), m.Item("Pizza", 1000, ["a"])]
    result = m.split_bill(items, ["a", "b"], "a", extras=100)
    assert result.unassigned == ["Ghost item"]
    assert result.people["b"].total == 0
    assert result.debts() == {}


@pytest.mark.parametrize("m", MODULES)
def test_payer_must_exist(m):
    with pytest.raises(ValueError):
        m.split_bill([], ["a"], "z")


@pytest.mark.parametrize("m", MODULES)
def test_random_bills_always_sum_exactly(m):
    rng = random.Random(42)
    for _ in range(500):
        people = [f"p{i}" for i in range(rng.randint(1, 6))]
        items = [
            m.Item(f"i{j}", rng.randint(-300, 5000), rng.sample(people, rng.randint(1, len(people))))
            for j in range(rng.randint(1, 12))
        ]
        extras = rng.randint(-500, 2000)
        result = m.split_bill(items, people, people[0], extras=extras)
        assert result.grand_total == sum(i.price for i in items) + extras


def test_parse_people():
    assert app_split.parse_people("Umair, Ali,  Sara, ali,,") == ["Umair", "Ali", "Sara"]
    assert app_split.parse_people("") == []


def test_skill_cli_run():
    out = skill_split.run({
        "people": ["Umair", "Ali", "Sara"], "payer": "Umair",
        "items": [
            {"name": "Zombie Burger", "line_total": 13.50, "shared_by": ["Ali"]},
            {"name": "Graveyard Nachos", "line_total": 8.95},
        ],
        "service_charge": 2.80, "total": 25.25,
    })
    assert out["debts"] == {"Ali": "£18.54", "Sara": "£3.35"}
    assert out["matches_printed_total"] is True


# --------------------------------------------------------------------------- #
# DESIGN.md demo fixture: The Lantern Kitchen, £56.00, four people
# --------------------------------------------------------------------------- #

from split_and_spell import sample  # noqa: E402

PEOPLE = sample.PEOPLE
TOTAL = app_split.to_pence(sample.TOTAL)


def test_fixture_items_add_up_to_56():
    assert sum(app_split.to_pence(p) for _, p in sample.ITEMS) == TOTAL == 5600


def test_fixture_equal_split():
    assert app_split.equal_split(TOTAL, PEOPLE) == {p: 1400 for p in PEOPLE}


def test_fixture_custom_amounts():
    amounts = {n: app_split.to_pence(v) for n, v in sample.CUSTOM.items()}
    check = app_split.check_custom(TOTAL, amounts)
    assert check.balanced and check.assigned == 5600
    assert app_split.check_custom(TOTAL, {**amounts, "Alex": 200}).remaining == 800   # "£8.00 left to assign"
    assert app_split.check_custom(TOTAL, {**amounts, "Alex": 1300}).remaining == -300  # "£3.00 over the bill total"
    with pytest.raises(ValueError):
        app_split.check_custom(TOTAL, {"Umair": -1})


def test_fixture_by_item():
    items = [app_split.Item(n, app_split.to_pence(p), sample.BY_ITEM[n]) for n, p in sample.ITEMS]
    result = app_split.split_bill(items, PEOPLE, "Umair")
    totals = {n: s.total for n, s in result.people.items()}
    assert totals == {"Umair": 1700, "Maya": 1900, "Sam": 1200, "Alex": 800}
    assert sum(totals.values()) == 5600 and result.unassigned == []


def test_ten_pounds_three_ways():
    assert app_split.equal_split(1000, ["A", "B", "C"]) == {"A": 334, "B": 333, "C": 333}
