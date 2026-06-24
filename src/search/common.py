from __future__ import annotations

import re
from typing import Iterable, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..matching import (
    is_junk_candidate,
    pick_alternative_matches,
    pick_best_match,
    pick_multipack_matches,
)
from ..models import PriceResult
from ..scrapers.base import parse_german_price

PRICE_RE = re.compile(r"(\d+[,.]\d{2})\s*€")

Candidate = tuple[str, str, float, Optional[float], bool]


def candidate_to_price_result(
    retailer: str,
    title: str,
    url: str,
    price: float,
    original: Optional[float],
    in_stock: bool,
) -> PriceResult:
    display = title.split(" https://")[0].split(" http://")[0].strip()
    discount = None
    if original and original > price:
        discount = round((original - price) / original * 100, 1)
    return PriceResult(
        name=display,
        price=price,
        url=url,
        retailer=retailer,
        original_price=original,
        discount_pct=discount,
        in_stock=in_stock,
    )


def find_multipack_offers(
    query: str,
    reference_pack: str,
    candidates: Iterable[Candidate],
    retailer: str,
    *,
    exclude_urls: Iterable[str] = (),
) -> list[PriceResult]:
    results: list[PriceResult] = []
    for title, url, price, original, in_stock in pick_multipack_matches(
        query, reference_pack, candidates, exclude_urls=exclude_urls
    ):
        results.append(
            candidate_to_price_result(retailer, title, url, price, original, in_stock)
        )
    return results


def find_alternative_offers(
    query: str,
    pack_size: str,
    candidates: Iterable[Candidate],
    retailer: str,
    *,
    exclude_url: str = "",
) -> list[PriceResult]:
    results: list[PriceResult] = []
    for title, url, price, original, in_stock in pick_alternative_matches(
        query, pack_size, candidates, exclude_url=exclude_url
    ):
        results.append(
            candidate_to_price_result(retailer, title, url, price, original, in_stock)
        )
    return results


def parse_search_page_products(
    html: str,
    site_base: str,
    *,
    shop_path: str = "/shop/",
) -> list[tuple[str, str, float, Optional[float], bool]]:
    """Extract (title, url, price, original, in_stock) from a retailer search page."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[tuple[str, str, float, Optional[float], bool]] = []
    seen: set[str] = set()

    for heading in soup.find_all(["h2", "h3", "h4"]):
        title = heading.get_text(" ", strip=True)
        if len(title) < 10 or is_junk_candidate(title):
            continue

        block = heading
        price = None
        original = None
        link = ""
        for _ in range(8):
            if block is None:
                break
            text = block.get_text(" ", strip=True)
            if price is None:
                m = PRICE_RE.search(text)
                if m:
                    price = parse_german_price(m.group(1))
            if not original:
                uvp = re.search(r"UVP\s*([\d.,]+)\s*€", text, re.IGNORECASE)
                if uvp:
                    original = parse_german_price(uvp.group(1))
            if not link:
                a = block.find("a", href=lambda h: h and shop_path in h)
                if a:
                    link = urljoin(site_base, a["href"])
            if price is not None and link:
                break
            block = block.parent

        if price is None or not link:
            continue
        key = f"{title}|{link}"
        if key in seen:
            continue
        seen.add(key)
        results.append((title, link, price, original, True))

    if results:
        return results

    # Fallback: any shop link with a nearby price
    for a in soup.find_all("a", href=lambda h: h and shop_path in h):
        title = (a.get("aria-label") or a.get("title") or a.get_text(" ", strip=True)).strip()
        if len(title) < 10 or is_junk_candidate(title):
            continue
        parent = a.parent
        for _ in range(6):
            if parent is None:
                break
            text = parent.get_text(" ", strip=True)
            m = PRICE_RE.search(text)
            if m:
                price = parse_german_price(m.group(1))
                if price is not None:
                    link = urljoin(site_base, a["href"])
                    key = f"{title}|{link}"
                    if key not in seen:
                        seen.add(key)
                        results.append((title, link, price, None, True))
                break
            parent = parent.parent

    return results


def best_search_match(
    query: str,
    pack_size: str,
    candidates: Iterable[tuple[str, str, float, Optional[float], bool]],
) -> Optional[tuple[str, str, float, Optional[float], bool]]:
    match = pick_best_match(query, pack_size, candidates)
    if not match:
        return None
    title, url, price, original_str, in_stock = match
    original = float(original_str) if original_str else None
    return title, url, price, original, in_stock
