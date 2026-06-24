from __future__ import annotations

from typing import List, Optional
from urllib.parse import quote_plus

import requests

from ..models import PriceResult, RetailerSearchResult
from ..scrapers.base import USER_AGENT, REQUEST_TIMEOUT
from .common import (
    Candidate,
    best_search_match,
    candidate_to_price_result,
    find_alternative_offers,
    find_multipack_offers,
    parse_search_page_products,
)
from .queries import search_query_variants

SITE_BASE = "https://www.zooplus.de"


class ZooplusSearch:
    retailer = "zooplus"

    def collect_candidates(self, query: str, pack_size: str) -> List[Candidate]:
        candidates: List[Candidate] = []
        seen: set[str] = set()

        for search_q in search_query_variants(query, pack_size):
            url = f"{SITE_BASE}/search?q={quote_plus(search_q)}"
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept-Language": "de-DE,de;q=0.9"},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            for item in parse_search_page_products(response.text, SITE_BASE, shop_path="/shop/"):
                key = item[0] + item[1]
                if key not in seen:
                    seen.add(key)
                    candidates.append(item)
        return candidates

    def search_full(
        self, query: str, pack_size: str, *, hint_url: str = ""
    ) -> RetailerSearchResult:
        candidates = self.collect_candidates(query, pack_size)
        matched = best_search_match(query, pack_size, candidates)
        primary = None
        if matched:
            title, product_url, price, original, in_stock = matched
            primary = candidate_to_price_result(
                self.retailer, title, product_url, price, original, in_stock
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
