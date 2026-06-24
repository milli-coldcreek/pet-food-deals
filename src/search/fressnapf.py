from __future__ import annotations

from typing import List, Optional

import requests

from ..models import PriceResult, RetailerSearchResult
from ..scrapers.base import REQUEST_TIMEOUT, USER_AGENT, parse_german_price
from .common import (
    Candidate,
    best_search_match,
    candidate_to_price_result,
    find_alternative_offers,
    find_multipack_offers,
    hint_url_candidate,
)
from .queries import search_query_variants

API_BASE = "https://api.os.fressnapf.com/rest/v2/fressnapfDE"
SITE_BASE = "https://www.fressnapf.de"


def _product_title(product: dict) -> str:
    full = (product.get("fullName") or "").strip()
    if full:
        return full

    name = (product.get("name") or product.get("summary") or "").strip()
    brand = product.get("brandName") or product.get("brand") or product.get("manufacturer") or ""
    if isinstance(brand, dict):
        brand = brand.get("name", "")
    brand = str(brand).strip()
    if brand and brand.lower() not in name.lower():
        name = f"{brand} {name}".strip()
    return name


def _matching_blob(product: dict, url: str) -> str:
    return f"{_product_title(product)} {url}"


def _extract_price(product: dict) -> Optional[float]:
    pricing = product.get("pricing") or {}
    if isinstance(pricing, dict):
        current = pricing.get("current")
        if isinstance(current, dict) and current.get("value") is not None:
            return float(current["value"])

    price_info = product.get("price")
    if isinstance(price_info, (int, float)):
        return float(price_info)
    if isinstance(price_info, dict):
        if price_info.get("value") is not None:
            return float(price_info["value"])
        formatted = price_info.get("formattedValue")
        if formatted:
            parsed = parse_german_price(str(formatted))
            if parsed is not None:
                return parsed

    price_range = product.get("priceRange") or {}
    if isinstance(price_range, dict):
        for key in ("minPrice", "maxPrice"):
            entry = price_range.get(key)
            if isinstance(entry, dict) and entry.get("value") is not None:
                return float(entry["value"])

    volume_prices = product.get("volumePrices") or []
    if isinstance(volume_prices, list):
        values = [
            float(entry["value"])
            for entry in volume_prices
            if isinstance(entry, dict) and entry.get("value") is not None
        ]
        if values:
            return min(values)

    return None


def _product_url(product: dict) -> str:
    url_path = (product.get("url") or "").split("/inStock")[0].rstrip("/")
    if url_path.startswith("/"):
        return f"{SITE_BASE}{url_path}"
    if url_path.startswith("http"):
        return url_path
    if url_path:
        return f"{SITE_BASE}/{url_path}"
    code = product.get("code") or ""
    return f"{SITE_BASE}/p/{code}" if code else ""


class FressnapfSearch:
    retailer = "fressnapf"

    def collect_candidates(
        self, query: str, pack_size: str, *, hint_url: str = ""
    ) -> List[Candidate]:
        candidates: List[Candidate] = []
        seen: set[str] = set()

        hinted = hint_url_candidate(hint_url)
        if hinted:
            title, url, price, original, in_stock = hinted
            seen.add(url)
            candidates.append((title, url, price, original, in_stock))
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "de-DE,de;q=0.9",
        }

        for search_q in search_query_variants(query, pack_size):
            try:
                response = requests.get(
                    f"{API_BASE}/products/search",
                    params={"query": search_q, "pageSize": 30, "fields": "FULL"},
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
            except requests.RequestException:
                continue

            for product in response.json().get("products", []):
                url = _product_url(product)
                if not url or url in seen:
                    continue
                seen.add(url)
                match_text = _matching_blob(product, url)
                price = _extract_price(product)
                if not match_text or price is None:
                    continue
                original = None
                for key in ("wasPrice", "oldPrice", "strikeThroughPrice"):
                    old = product.get(key)
                    if isinstance(old, dict) and old.get("value"):
                        original = float(old["value"])
                        break
                stock = product.get("stock", {})
                in_stock = True
                if isinstance(stock, dict) and isinstance(stock.get("stockLevel"), (int, float)):
                    in_stock = stock["stockLevel"] > 0
                candidates.append((match_text, url, float(price), original, in_stock))
        return candidates

    def search_full(
        self, query: str, pack_size: str, *, hint_url: str = ""
    ) -> RetailerSearchResult:
        candidates = self.collect_candidates(query, pack_size, hint_url=hint_url)
        matched = best_search_match(query, pack_size, candidates)
        primary = None
        if matched:
            title, url, price, original, in_stock = matched
            primary = candidate_to_price_result(
                self.retailer, title, url, price, original, in_stock
            )
        exclude = primary.url if primary else ""
        exclude_urls = [exclude] if exclude else []
        alternatives = find_alternative_offers(
            query, pack_size, candidates, self.retailer, exclude_url=exclude
        )
        multipacks = find_multipack_offers(
            query, pack_size, candidates, self.retailer, exclude_urls=exclude_urls
        )
        return RetailerSearchResult(
            primary=primary, alternatives=alternatives, multipacks=multipacks
        )

    def search(self, query: str, pack_size: str) -> Optional[PriceResult]:
        return self.search_full(query, pack_size).primary
