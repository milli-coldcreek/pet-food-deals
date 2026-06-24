from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

DEFAULT_RETAILERS = ("fressnapf", "zooplus", "zooroyal")


@dataclass
class ProductWatch:
    name: str
    search_query: str
    pack_size: str
    pet: str = ""
    target_price: Optional[float] = None
    min_discount_pct: float = 10.0
    retailers: List[str] = field(default_factory=lambda: list(DEFAULT_RETAILERS))
    retailer_urls: Dict[str, str] = field(default_factory=dict)
    # Legacy: direct URL still supported for single-retailer checks
    url: Optional[str] = None

    @property
    def key(self) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", self.search_query.lower()).strip("-")
        pack = re.sub(r"[^a-z0-9]+", "-", self.pack_size.lower()).strip("-")
        return f"{slug}|{pack}"

    def state_key(self, retailer: str) -> str:
        return f"{self.key}|{retailer}"


@dataclass
class PriceResult:
    name: str
    price: float
    url: str
    retailer: str
    original_price: Optional[float] = None
    discount_pct: Optional[float] = None
    in_stock: bool = True
    currency: str = "EUR"

    @property
    def on_sale(self) -> bool:
        if self.discount_pct is not None and self.discount_pct > 0:
            return True
        if self.original_price is not None and self.original_price > self.price:
            return True
        return False


@dataclass
class DealAlert:
    product: ProductWatch
    price: PriceResult
    reason: str
    baseline_price: Optional[float] = None
    kind: str = "standard"
    primary_price: Optional[float] = None
    unit_price: Optional[float] = None
    unit_label: Optional[str] = None
    target_unit_price: Optional[float] = None


@dataclass
class RetailerSearchResult:
    primary: Optional[PriceResult]
    alternatives: List[PriceResult]
    multipacks: List[PriceResult]
