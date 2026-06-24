from __future__ import annotations

from typing import List, Optional
from urllib.parse import quote_plus

import requests

from ..models import PriceResult, RetailerSearchResult
from ..scrapers.base import USER_AGENT, REQUEST_TIMEOUT, fetch_price
from .common import (
    Candidate,
    best_search_match,
    candidate_to_price_result,
    find_alternative_offers,
    find_multipack_offers,
    hint_url_candidate,
    parse_search_page_products,
)
from .queries import search_query_variants

SITE_BASE = "https://www.zooplus.de"


def _refresh_zooplus_price(result: PriceResult) -> PriceResult:
    try:
        return fetch_price(result.url)
    except Exception:
        return result


class ZooplusSearch:
    retailer = "zooplus"

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
        candidates = self.collect_candidates(query, pack_size, hint_url=hint_url)
        matched = best_search_match(query, pack_size, candidates)
        primary = None
        if matched:
            title, product_url, price, original, in_stock = matched
            primary = candidate_to_price_result(
                self.retailer, title, product_url, price, original, in_stock
            )
            primary = _refresh_zooplus_price(primary)
        exclude = primary.url if primary else ""
        exclude_urls = [exclude] if exclude else []
        alternatives = find_alternative_offers(
            query, pack_size, candidates, self.retailer, exclude_url=exclude
        )
        refreshed_alts: List[PriceResult] = []
        for alt in alternatives:
            refreshed_alts.append(_refresh_zooplus_price(alt))
        multipacks = find_multipack_offers(
            query, pack_size, candidates, self.retailer, exclude_urls=exclude_urls
        )
        refreshed_mp: List[PriceResult] = []
        for mp in multipacks:
            refreshed_mp.append(_refresh_zooplus_price(mp))
        return RetailerSearchResult(
            primary=primary, alternatives=refreshed_alts, multipacks=refreshed_mp
        )

    def search(self, query: str, pack_size: str) -> Optional[PriceResult]:
        return self.search_full(query, pack_size).primary
