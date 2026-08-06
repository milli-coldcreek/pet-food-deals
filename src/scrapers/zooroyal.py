from __future__ import annotations

import json
import re
from typing import Any, Optional

from bs4 import BeautifulSoup

from ..matching import parse_pack_size
from ..models import PriceResult
from .base import BaseScraper, http_get, parse_german_price, register_scraper

# Ignore tiny misreads (savings badges, per-kg, single pouch) for multipacks.
PACK_TOTAL_MIN = 6.0
PACK_TOTAL_MAX = 250.0
MIN_UNIT_EUR = {
    ("g", 85): 0.70,
    ("g", 100): 0.70,
    ("g", 400): 1.20,
    ("g", 800): 1.80,
}

SAVINGS_CONTEXT_RE = re.compile(
    r"(du\s+sparst|ersparnis|sie\s+sparen|gespart)",
    re.IGNORECASE,
)
PER_KG_CONTEXT_RE = re.compile(r"/\s*kg|pro\s*kg|je\s*kg", re.IGNORECASE)
HISTORY_CONTEXT_RE = re.compile(
    r"(30[\s-]*tage|tiefstpreis|preis[\s-]*historie|durchschnitt)",
    re.IGNORECASE,
)
EURO_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*[,.]\d{2})\s*€")


class ZooroyalScraper(BaseScraper):
    retailer = "zooroyal"

    def scrape(self, url: str) -> PriceResult:
        response = http_get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except json.JSONDecodeError:
                continue
            product = self._find_product_ld(data)
            if product:
                return self._parse_ld_product(product, url, soup)

        title = soup.find("h1")
        name = title.get_text(strip=True) if title else "Unknown product"
        price, original, discount = self._extract_from_html(soup, name=name, url=url)
        if price is None:
            raise ValueError("Could not parse Zooroyal price")

        return PriceResult(
            name=name,
            price=price,
            url=url,
            retailer=self.retailer,
            original_price=original,
            discount_pct=discount,
            in_stock=True,
        )

    def _find_product_ld(self, data: Any) -> Optional[dict]:
        if isinstance(data, list):
            for item in data:
                found = self._find_product_ld(item)
                if found:
                    return found
        if not isinstance(data, dict):
            return None

        type_value = data.get("@type")
        types = type_value if isinstance(type_value, list) else [type_value]
        types = [str(t).lower() for t in types if t]

        if "product" in types and self._offers_price(data) is not None:
            return data

        # Modern Zooroyal pages use ProductGroup + hasVariant.
        if "productgroup" in types:
            variants = data.get("hasVariant") or data.get("variesBy") or []
            if isinstance(variants, dict):
                variants = [variants]
            if isinstance(variants, list):
                for variant in variants:
                    if not isinstance(variant, dict):
                        continue
                    if self._offers_price(variant) is not None:
                        return variant
                # Fall back to first variant with a name even without price.
                for variant in variants:
                    if isinstance(variant, dict) and variant.get("name"):
                        return variant

        graph = data.get("@graph")
        if isinstance(graph, list):
            return self._find_product_ld(graph)

        for key in ("hasVariant", "mainEntity", "itemListElement"):
            nested = data.get(key)
            if nested is not None:
                found = self._find_product_ld(nested)
                if found:
                    return found
        return None

    def _offers_price(self, product: dict) -> Optional[float]:
        offers = product.get("offers")
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if not isinstance(offers, dict):
            return None
        return parse_german_price(str(offers.get("price", "")))

    def _parse_ld_product(
        self, product: dict, url: str, soup: BeautifulSoup
    ) -> PriceResult:
        name = product.get("name", "Unknown product")
        offers = product.get("offers")
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if not isinstance(offers, dict):
            offers = {}

        price = parse_german_price(str(offers.get("price", "")))
        html_price, original, discount = self._extract_from_html(
            soup, name=name, url=url
        )
        if price is None or not self._price_plausible(price, name, url):
            price = html_price
        if price is None:
            raise ValueError("Could not parse Zooroyal price")

        availability = str(offers.get("availability", "")).lower()
        in_stock = "outofstock" not in availability

        return PriceResult(
            name=name,
            price=price,
            url=url,
            retailer=self.retailer,
            original_price=original if original and original > price else None,
            discount_pct=discount,
            in_stock=in_stock,
        )

    def _min_plausible_total(self, name: str, url: str) -> Optional[float]:
        pack = None
        for text in (name, url):
            pack = parse_pack_size(text)
            if pack:
                break
        if pack is None:
            return None
        unit_key = (pack.unit, int(round(pack.amount)))
        per_piece = MIN_UNIT_EUR.get(unit_key)
        if per_piece is None and pack.unit == "g":
            per_piece = 0.60 if pack.amount < 200 else 1.00
        if per_piece is None:
            return None
        return round(pack.count * per_piece, 2)

    def _price_plausible(self, price: float, name: str, url: str) -> bool:
        if not (PACK_TOTAL_MIN <= price <= PACK_TOTAL_MAX):
            return False
        minimum = self._min_plausible_total(name, url)
        if minimum is not None and price < minimum:
            return False
        return True

    def _context_ok(self, context: str) -> bool:
        return not (
            SAVINGS_CONTEXT_RE.search(context)
            or PER_KG_CONTEXT_RE.search(context)
            or HISTORY_CONTEXT_RE.search(context)
        )

    def _extract_from_html(
        self,
        soup: BeautifulSoup,
        *,
        name: str = "",
        url: str = "",
    ) -> tuple[Optional[float], Optional[float], Optional[float]]:
        text = soup.get_text(" ", strip=True)

        original = None
        discount = None

        uvp_match = re.search(r"UVP\s*([\d.,]+)\s*€", text, re.IGNORECASE)
        if uvp_match:
            original = parse_german_price(uvp_match.group(1))

        discount_match = re.search(r"-\s*(\d+)\s*%", text)
        if discount_match:
            discount = float(discount_match.group(1))

        def collect(window: str) -> list[float]:
            found: list[float] = []
            for match in EURO_RE.finditer(window):
                value = parse_german_price(match.group(1))
                if value is None:
                    continue
                context = window[max(0, match.start() - 40) : match.end() + 40]
                if not self._context_ok(context):
                    continue
                if original is not None and value >= original:
                    continue
                if self._price_plausible(value, name, url):
                    found.append(value)
            return found

        candidates: list[float] = []

        # Best signal: first plausible sell price right after UVP.
        if uvp_match is not None:
            after_uvp = text[uvp_match.end() : uvp_match.end() + 180]
            after_prices = collect(after_uvp)
            if after_prices:
                candidates.append(after_prices[0])

        cart_idx = text.lower().find("in den warenkorb")
        if cart_idx > 0:
            candidates.extend(collect(text[max(0, cart_idx - 160) : cart_idx + 80]))

        candidates.extend(collect(text))

        meta = soup.find("meta", property="product:price:amount")
        if meta and meta.get("content"):
            meta_price = parse_german_price(meta["content"])
            if meta_price is not None and self._price_plausible(meta_price, name, url):
                candidates.insert(0, meta_price)

        price = candidates[0] if candidates else None

        if original and price and original > price and discount is None:
            discount = round((original - price) / original * 100, 1)

        return price, original, discount


register_scraper(ZooroyalScraper())
