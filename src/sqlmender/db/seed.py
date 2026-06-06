"""Deterministic seed data generation (no external deps; seeded RNG so the DB is
reproducible). ~200+ rows per table."""

from __future__ import annotations

import random
from datetime import date, timedelta

CATEGORIES = [
    ("Electronics", "Devices and gadgets"),
    ("Books", "Printed and digital books"),
    ("Clothing", "Apparel and accessories"),
    ("Home", "Home and kitchen goods"),
    ("Sports", "Sporting goods and outdoor"),
    ("Toys", "Toys and games"),
    ("Beauty", "Beauty and personal care"),
    ("Garden", "Garden and outdoor living"),
]
FIRST = [
    "Alice",
    "Bob",
    "Carol",
    "David",
    "Eve",
    "Frank",
    "Grace",
    "Heidi",
    "Ivan",
    "Judy",
    "Mallory",
    "Niaj",
    "Olivia",
    "Peggy",
    "Rupert",
    "Sybil",
    "Trent",
    "Victor",
]
LAST = [
    "Smith",
    "Jones",
    "Patel",
    "Kim",
    "Garcia",
    "Nguyen",
    "Khan",
    "Silva",
    "Cohen",
    "Rossi",
    "Mueller",
    "Tanaka",
    "Lopez",
    "Haddad",
    "Novak",
    "Singh",
]
CITIES = [
    ("London", "UK"),
    ("Paris", "France"),
    ("Berlin", "Germany"),
    ("Madrid", "Spain"),
    ("Rome", "Italy"),
    ("Chennai", "India"),
    ("Tokyo", "Japan"),
    ("Toronto", "Canada"),
    ("Austin", "USA"),
    ("Sydney", "Australia"),
]
STATUSES = ["pending", "shipped", "delivered", "cancelled", "returned"]
ADJ = ["Classic", "Deluxe", "Mini", "Pro", "Eco", "Smart", "Ultra", "Vintage", "Premium", "Basic"]
NOUN = ["Widget", "Gadget", "Gizmo", "Device", "Tool", "Kit", "Set", "Pack", "Bundle", "Unit"]


def generate(seed: int = 42) -> dict[str, list[tuple]]:
    rng = random.Random(seed)
    base = date(2023, 1, 1)

    categories = [(i + 1, n, d) for i, (n, d) in enumerate(CATEGORIES)]

    customers = []
    for cid in range(1, 211):
        fn, ln = rng.choice(FIRST), rng.choice(LAST)
        city, country = rng.choice(CITIES)
        created = base + timedelta(days=rng.randint(0, 700))
        customers.append(
            (
                cid,
                fn,
                ln,
                f"{fn.lower()}.{ln.lower()}{cid}@example.com",
                city,
                country,
                created.isoformat(),
            )
        )

    products = []
    for pid in range(1, 221):
        cat = rng.randint(1, len(CATEGORIES))
        name = f"{rng.choice(ADJ)} {rng.choice(NOUN)} {pid}"
        price = round(rng.uniform(5, 500), 2)
        stock = rng.randint(0, 500)
        products.append((pid, name, cat, price, stock))

    orders = []
    for oid in range(1, 301):
        cust = rng.randint(1, 210)
        od = base + timedelta(days=rng.randint(0, 800))
        status = rng.choice(STATUSES)
        orders.append((oid, cust, od.isoformat(), status, 0.0))  # total filled below

    order_items = []
    oi_id = 1
    totals: dict[int, float] = {}
    for oid in range(1, 301):
        for _ in range(rng.randint(1, 4)):
            pid = rng.randint(1, 220)
            qty = rng.randint(1, 5)
            unit = round(rng.uniform(5, 500), 2)
            order_items.append((oi_id, oid, pid, qty, unit))
            totals[oid] = totals.get(oid, 0.0) + qty * unit
            oi_id += 1
    orders = [(o[0], o[1], o[2], o[3], round(totals.get(o[0], 0.0), 2)) for o in orders]

    reviews = []
    for rid in range(1, 251):
        reviews.append(
            (
                rid,
                rng.randint(1, 220),
                rng.randint(1, 210),
                rng.randint(1, 5),
                None,
                (base + timedelta(days=rng.randint(0, 800))).isoformat(),
            )
        )

    return {
        "categories": categories,
        "customers": customers,
        "products": products,
        "orders": orders,
        "order_items": order_items,
        "reviews": reviews,
    }
