from __future__ import annotations

import os
import sys
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
from .zooroyal_parser import enrich_zooroyal_candidate, parse_zooroyal_search_page

SITE_BASE = "https://www.zooroyal.de"
MAX_ENRICH = 5


class ZooroyalSearch:
    retailer = "zooroyal"

    def collect_candidates(
        self, query: str, pack_size: str, *, hint_url: str = ""
    ) -> List[Candidate]:
        candidates: List[Candidate] = []
        seen: set[str] = set()
        enrich_budget = MAX_ENRICH

        if hint_url:
            hinted = enrich_zooroyal_candidate(
                ("", hint_url.rstrip("/") + "/", None, None, True)
            )
            if hinted:
                title, url, price, original, in_stock = hinted
                if price is not None:
                    seen.add(url)
                    candidates.append((title, url, price, original, in_stock))

        for search_q in search_query_variants(query, pack_size):
            if not search_q:
                continue
            try:
                response = requests.get(
                    f"{SITE_BASE}/search?q={quote_plus(search_q)}",
                    headers={"User-Agent": USER_AGENT, "Accept-Language": "de-DE,de;q=0.9"},
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
            except requests.RequestException:
                continue

            page_items = parse_zooroyal_search_page(response.text, SITE_BASE)
            if not page_items:
                page_items = parse_search_page_products(
                    response.text, SITE_BASE, shop_path="/p/"
                )

            if os.environ.get("PET_DEAL_DEBUG"):
                print(
                    f"  DEBUG [zooroyal] query={search_q!r} candidates={len(page_items)}",
                    file=sys.stderr,
                )

            for item in page_items:
                title, url, price, original, in_stock = item
                if url in seen:
                    continue

                if price is None and enrich_budget > 0:
                    enriched = enrich_zooroyal_candidate(item)
                    enrich_budget -= 1
                    if enriched is None:
                        continue
                    title, url, price, original, in_stock = enriched

                if price is None:
                    continue

                seen.add(url)
                candidates.append((title, url, price, original, in_stock))

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
