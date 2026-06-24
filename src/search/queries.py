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
    return variants
