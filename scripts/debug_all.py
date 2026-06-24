"""Run: python scripts/debug_all.py"""
from __future__ import annotations

import requests

from src.matching import pick_best_match, score_search_result
from src.search.fressnapf import FressnapfSearch
from src.search.zooplus import ZooplusSearch
from src.search.zooroyal import ZooroyalSearch

Q = "Royal Canin Instinctive in Soße"
P = "12x85g"

print("=== Fressnapf API ===")
r = requests.get(
    "https://api.os.fressnapf.com/rest/v2/fressnapfDE/products/search",
    params={"query": Q, "pageSize": 5, "fields": "FULL"},
    headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
    timeout=30,
)
print("status", r.status_code)
data = r.json()
print("products", len(data.get("products", [])))
for prod in data.get("products", [])[:3]:
    from src.search.fressnapf import _product_title, _product_url

    url = _product_url(prod)
    title = _product_title(prod, url)
    price = (prod.get("price") or {}).get("value")
    score = score_search_result(Q, P, title, url=url)
    print(f"  score={score:6.1f} price={price} title={title[:70]!r}")

print("\n=== FressnapfSearch ===")
print(FressnapfSearch().search(Q, P))

print("\n=== Zooplus raw ===")
zs = ZooplusSearch()
resp = requests.get(
    "https://www.zooplus.de/search?q=Royal+Canin+Instinctive",
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30,
)
print("status", resp.status_code, "len", len(resp.text))
for name, fn in [
    ("shop_links", zs._from_shop_links),
    ("next_data", zs._from_next_data),
    ("html", zs._from_html),
]:
    cands = list(fn(resp.text))
    print(f"  {name}: {len(cands)} candidates")
    for c in cands[:2]:
        s = score_search_result(Q, P, c[0], url=c[1])
        print(f"    score={s:6.1f} {c[0][:60]!r}")

print("\n=== ZooplusSearch ===")
print(ZooplusSearch().search(Q, P))

print("\n=== ZooroyalSearch ===")
print(ZooroyalSearch().search(Q, P))
