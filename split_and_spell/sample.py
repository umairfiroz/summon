"""The demo fixture from DESIGN.md section 14. Always labelled "Sample receipt"."""

MERCHANT = "The Lantern Kitchen"
CURRENCY = "GBP"
TOTAL = "56.00"

ITEMS = [
    ("Pumpkin pasta", "14.00"),
    ("Mushroom risotto", "16.00"),
    ("Margherita pizza", "12.00"),
    ("Garlic bread", "6.00"),
    ("Apple crumble", "8.00"),
]

PEOPLE = ["Umair", "Maya", "Sam", "Alex"]

# By-item allocation from DESIGN.md: Umair £17, Maya £19, Sam £12, Alex £8.
BY_ITEM = {
    "Pumpkin pasta": ["Umair"],
    "Mushroom risotto": ["Maya"],
    "Margherita pizza": ["Sam"],
    "Garlic bread": ["Umair", "Maya"],
    "Apple crumble": ["Alex"],
}

# Custom amounts from DESIGN.md.
CUSTOM = {"Umair": "18.00", "Maya": "16.00", "Sam": "12.00", "Alex": "10.00"}
