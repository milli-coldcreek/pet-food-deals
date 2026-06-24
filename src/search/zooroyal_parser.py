from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..matching import is_junk_candidate
from ..scrapers.base import parse_german_price
from .common import PRICE_RE, Candidate

PRODUCT_PATH = re.compile(r"/p/[^/]+/\d+")


def _normalize_product_url(site_base: str, href: str) -> str:
    link = urljoin(site_base, href.split("?")[0])
    return link if link.endswith("/") else f"{link}/"


def _title_from_link(a) -> str:
    for attr in ("aria-label", "title", "data-name"):
        value = (a.get(attr) or "").strip()
        if len(value) >= 8:
            return value
    img = a.find("img")
    if img:
        for attr in ("alt", "title"):
            value = (img.get(attr) or "").strip()
            if len(value) >= 8:
                return value
    return a.get_text(" ", strip=True)


def _prices_from_text(text: str) -> tuple[Optional[float], Optional[float]]:
    prices = [parse_german_price(m.group(1)) for m in PRICE_RE.finditer(text)]
    prices = [p for p in prices if p is not None]
    if not prices:
        return None, None
    current = prices[0]
    original = None
    uvp = re.search(r"UVP\s*([\d.,]+)\s*€", text, re.IGNORECASE)
    if uvp:
        original = parse_german_price(uvp.group(1))
    elif len(prices) > 1:
        original = max(prices)
    return current, original


def parse_zooroyal_search_page(html: str, site_base: str) -> list[Candidate]:
    """ZooRoyal lists products as /p/<slug>/<id>/ links, often without h2 headings."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[Candidate] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not PRODUCT_PATH.search(href):
            continue

        link = _normalize_product_url(site_base, href)
        if link in seen:
            continue

        title = _title_from_link(a)
        if len(title) < 8 or is_junk_candidate(title):
            continue

        price = None
        original = None
        block = a
        for _ in range(12):
            if block is None:
                break
            text = block.get_text(" ", strip=True)
            price, original = _prices_from_text(text)
            if price is not None:
                break
            block = block.parent

        seen.add(link)
        results.append((title, link, price, original, True))

    return results


def enrich_zooroyal_candidate(candidate: Candidate) -> Optional[Candidate]:
    """Fetch product page when search listing omits price."""
    title, url, price, original, in_stock = candidate
    if price is not None:
        return candidate

    from ..scrapers.zooroyal import ZooroyalScraper

    try:
        scraped = ZooroyalScraper().scrape(url)
    except Exception:
        return None

    return (
        scraped.name or title,
        url,
        scraped.price,
        scraped.original_price or original,
        scraped.in_stock,
    )
