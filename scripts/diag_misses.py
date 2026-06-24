"""Diagnose MISS reasons. Run: python scripts/diag_misses.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from src.config import load_products
from src.matching import product_matches, score_search_result
from src.search.common import parse_search_page_products
from src.search.fressnapf import (
    FressnapfSearch,
    _extract_price,
    _matching_blob,
    _product_title,
    _product_url,
)
from src.search.zooplus import ZooplusSearch
from src.search.zooroyal import ZooroyalSearch
from src.scrapers.base import USER_AGENT

API = "https://api.os.fressnapf.com/rest/v2/fressnapfDE/products/search"


def diag_fressnapf(query: str, pack: str) -> None:
    print(f"\n--- Fressnapf: {query!r} / {pack} ---")
    r = requests.get(
        API,
        params={"query": query, "pageSize": 8, "fields": "FULL"},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=30,
    )
    prods = r.json().get("products", [])
    print(f"  API products: {len(prods)}")
    priced = 0
    for p in prods[:5]:
        url = _product_url(p)
        title = _product_title(p)
        blob = _matching_blob(p, url)
        price = _extract_price(p)
        if price is not None:
            priced += 1
        score = score_search_result(query, pack, blob, url=url) if price else -1
        ok = product_matches(query, pack, blob, url=url) if price else False
        print(f"  [{score:5.0f}] €{price} match={ok} | {title[:65]}")
    print(f"  priced: {priced}/{len(prods)}")
    print(f"  FressnapfSearch: {FressnapfSearch().search(query, pack)}")


def diag_html(retailer: str, base: str, shop_path: str, query: str, pack: str) -> None:
    print(f"\n--- {retailer}: {query!r} / {pack} ---")
    from urllib.parse import quote_plus

    url = f"{base}/search?q={quote_plus(query)}"
    r = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "de-DE,de;q=0.9"},
        timeout=30,
    )
    cands = parse_search_page_products(r.text, base, shop_path=shop_path)
    print(f"  HTML candidates: {len(cands)}")
    for title, link, price, *_ in cands[:5]:
        score = score_search_result(query, pack, title, url=link)
        print(f"  [{score:5.0f}] €{price:.2f} | {title[:65]}")
    if retailer == "zooplus":
        print(f"  ZooplusSearch: {ZooplusSearch().search(query, pack)}")
    else:
        print(f"  ZooroyalSearch: {ZooroyalSearch().search(query, pack)}")


def main() -> None:
    cases = [
        ("Royal Canin Instinctive 7+ in Soße", "12x85g"),
        ("Feringa Classic Meat Menü", "12x400g"),
        ("Feringa Classic Meat Menü", "24x400g"),
        ("Cosma Asia in Jelly", "12x400g"),
        ("PREMIERE Meati Nassfutter Hund", "6x800g"),
    ]
    for query, pack in cases:
        diag_fressnapf(query, pack)
        diag_html("zooplus", "https://www.zooplus.de", "/shop/", query, pack)

    print("\n=== products.yaml loaded ===")
    for p in load_products():
        print(f"  {p.name} -> {p.search_query!r} / {p.pack_size}")


if __name__ == "__main__":
    main()
