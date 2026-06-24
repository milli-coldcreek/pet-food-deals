import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from src.matching import product_matches, score_search_result
from src.search.fressnapf import FressnapfSearch, _product_title, _product_url

Q = "Royal Canin Instinctive in Soße"
P = "12x85g"

lines = []
r = requests.get(
    "https://api.os.fressnapf.com/rest/v2/fressnapfDE/products/search",
    params={"query": Q, "pageSize": 5, "fields": "FULL"},
    headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
    timeout=30,
)
lines.append(f"HTTP {r.status_code}")
data = r.json()
prods = data.get("products", [])
lines.append(f"products: {len(prods)}")
for i, prod in enumerate(prods[:3]):
    url = _product_url(prod)
    title = _product_title(prod)
    match_text = f"{title} {url}"
    price = prod.get("price")
    lines.append(f"\n--- product {i} ---")
    lines.append(f"keys: {list(prod.keys())[:15]}")
    lines.append(f"price field: {price!r}")
    lines.append(f"title: {title[:100]!r}")
    lines.append(f"url: {url!r}")
    lines.append(f"product_matches: {product_matches(Q, P, match_text, url=url)}")
    lines.append(f"score: {score_search_result(Q, P, match_text, url=url)}")

lines.append(f"\nFressnapfSearch: {FressnapfSearch().search(Q, P)!r}")

open("smoke.txt", "w", encoding="utf-8").write("\n".join(lines))
print("wrote smoke.txt")
