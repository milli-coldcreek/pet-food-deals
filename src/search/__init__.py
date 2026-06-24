from __future__ import annotations

import os
import sys
from typing import Dict, Optional

import requests

from ..models import PriceResult, ProductWatch, RetailerSearchResult
from .fressnapf import FressnapfSearch
from .zooplus import ZooplusSearch
from .zooroyal import ZooroyalSearch

ALL_RETAILERS = ("fressnapf", "zooplus", "zooroyal")

_SEARCHERS = {
    "fressnapf": FressnapfSearch(),
    "zooplus": ZooplusSearch(),
    "zooroyal": ZooroyalSearch(),
}


def search_retailer_full(retailer: str, product: ProductWatch) -> RetailerSearchResult:
    searcher = _SEARCHERS.get(retailer)
    if searcher is None:
        raise ValueError(f"Unknown retailer: {retailer}")

    try:
        hint_url = (product.retailer_urls or {}).get(retailer, "")
        return searcher.search_full(
            product.search_query, product.pack_size, hint_url=hint_url
        )
    except requests.RequestException as exc:
        if os.environ.get("PET_DEAL_DEBUG"):
            print(f"  DEBUG network error: {exc}", file=sys.stderr)
        return RetailerSearchResult(primary=None, alternatives=[], multipacks=[])


def search_retailer(retailer: str, product: ProductWatch) -> Optional[PriceResult]:
    return search_retailer_full(retailer, product).primary


def search_all_retailers(product: ProductWatch) -> Dict[str, Optional[PriceResult]]:
    return {r: search_retailer(r, product) for r in product.retailers}
