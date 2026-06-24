from __future__ import annotations

from typing import List


def search_query_variants(query: str, pack_size: str) -> List[str]:
    """Build search strings: original, with pack, and common DE/EN swaps."""
    variants: List[str] = []

    def add(q: str) -> None:
        q = (q or "").strip()
        if q and q not in variants:
            variants.append(q)

    add(query)
    add(f"{query} {pack_size}".strip())

    replacements = (
        ("Meat", "Fleisch"),
        ("Fleisch", "Meat"),
        ("Jelly", "Gelee"),
        ("Gelee", "Jelly"),
        ("Soße", "Sosse"),
        ("Sosse", "Soße"),
        ("Menü", "Menu"),
        ("Menu", "Menü"),
    )
    for old, new in replacements:
        if old in query:
            add(query.replace(old, new))
            add(f"{query.replace(old, new)} {pack_size}".strip())

    ascii_q = (
        query.replace("ß", "ss")
        .replace("ü", "u")
        .replace("ö", "o")
        .replace("ä", "a")
    )
    add(ascii_q)
    add(f"{ascii_q} {pack_size}".strip())

    # Shorter queries for shops with weak full-string search
    if " in " in query:
        add(query.split(" in ", 1)[0].strip())
        add(f"{query.split(' in ', 1)[0].strip()} {pack_size}".strip())

    for old, new in (("7+", "7"), ("7+", "+7"), ("+7", "7")):
        if old in query:
            shortened = query.replace(old, new)
            add(shortened)
            add(f"{shortened} {pack_size}".strip())
            if " in " in shortened:
                add(shortened.split(" in ", 1)[0].strip())

    return variants
