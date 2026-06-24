from __future__ import annotations

import json
import re
from typing import Any, List, Optional
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from ..models import PriceResult
from .base import BaseScraper, http_get, parse_german_price, register_scraper

PACK_TOTAL_MIN = 3.0
PACK_TOTAL_MAX = 250.0


class ZooplusScraper(BaseScraper):
    retailer = "zooplus"

    def scrape(self, url: str) -> PriceResult:
        response = http_get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        next_data = soup.find("script", id="__NEXT_DATA__")
        if not next_data or not next_data.string:
            raise ValueError("Could not find Zooplus product data on page")

        data = json.loads(next_data.string)
        variant_id = self._variant_id_from_url(url)
        product = self._extract_product(data)
        if product is None:
            raise ValueError("Could not parse Zooplus product from page data")

        name = product.get("name") or product.get("title") or "Unknown product"
        price = self._best_pack_price(data, variant_id=variant_id)
        if price is None:
            price = self._extract_price(product)
        if price is None:
            raise ValueError("Could not parse Zooplus price")

        original = self._extract_original_price(product, price)
        discount = self._extract_discount(product, price, original)
        in_stock = self._extract_stock(product)

        return PriceResult(
            name=name,
            price=price,
            url=url,
            retailer=self.retailer,
            original_price=original,
            discount_pct=discount,
            in_stock=in_stock,
        )

    def _variant_id_from_url(self, url: str) -> Optional[str]:
        params = parse_qs(urlparse(url).query)
        values = params.get("activeVariant") or params.get("variant")
        return values[0] if values else None

    def _extract_product(self, data: Any) -> Optional[dict]:
        candidates = list(self._walk_dicts(data))
        for item in candidates:
            if isinstance(item, dict) and self._looks_like_product(item):
                return item
        return None

    def _looks_like_product(self, item: dict) -> bool:
        has_name = any(k in item for k in ("name", "title", "productName"))
        has_price = any(
            k in item
            for k in (
                "price",
                "currentPrice",
                "offerPrice",
                "sellingPrice",
                "discountedPriceRaw",
                "minArticlePriceRaw",
            )
        )
        return has_name and has_price

    def _walk_dicts(self, node: Any):
        if isinstance(node, dict):
            yield node
            for value in node.values():
                yield from self._walk_dicts(value)
        elif isinstance(node, list):
            for value in node:
                yield from self._walk_dicts(value)

    def _node_matches_variant(self, item: dict, variant_id: Optional[str]) -> bool:
        if not variant_id:
            return True
        for key in ("articleId", "variantId", "id", "shopIdentifier"):
            value = item.get(key)
            if value is not None and str(value) == variant_id:
                return True
        return False

    def _best_pack_price(self, data: Any, *, variant_id: Optional[str]) -> Optional[float]:
        def collect_prices(*, require_variant: bool) -> List[float]:
            prices: List[float] = []
            for item in self._walk_dicts(data):
                if not isinstance(item, dict):
                    continue
                if require_variant and variant_id and not self._node_matches_variant(
                    item, variant_id
                ):
                    continue
                for key in ("discountedPriceRaw", "discountPriceRaw"):
                    parsed = self._parse_price_value(item.get(key))
                    if parsed is not None and PACK_TOTAL_MIN <= parsed <= 22:
                        prices.append(parsed)
            return prices

        prices = collect_prices(require_variant=True)
        if not prices and variant_id:
            prices = collect_prices(require_variant=False)
        if prices:
            return min(prices)

        list_prices: List[float] = []
        for item in self._walk_dicts(data):
            if not isinstance(item, dict):
                continue
            for key in ("minArticlePriceRaw", "price", "currentPrice", "offerPrice"):
                parsed = self._parse_price_value(item.get(key))
                if parsed is not None and PACK_TOTAL_MIN <= parsed <= PACK_TOTAL_MAX:
                    list_prices.append(parsed)
        return min(list_prices) if list_prices else None

    def _extract_price(self, product: dict) -> Optional[float]:
        for key in ("price", "currentPrice", "offerPrice", "sellingPrice", "discountedPrice"):
            value = product.get(key)
            parsed = self._parse_price_value(value)
            if parsed is not None:
                return parsed

        variants = product.get("variants") or product.get("articleVariants") or []
        if isinstance(variants, list):
            for variant in variants:
                if isinstance(variant, dict):
                    parsed = self._extract_price(variant)
                    if parsed is not None:
                        return parsed
        return None

    def _extract_original_price(self, product: dict, current: float) -> Optional[float]:
        for key in ("originalPrice", "listPrice", "recommendedRetailPrice", "rrp", "uvp"):
            value = product.get(key)
            parsed = self._parse_price_value(value)
            if parsed is not None and parsed > current:
                return parsed

        for key in ("minArticlePriceRaw", "price", "currentPrice"):
            parsed = self._parse_price_value(product.get(key))
            if parsed is not None and parsed > current:
                return parsed

        discount = product.get("discount") or product.get("discountPercentage")
        if isinstance(discount, str):
            match = re.search(r"(\d+)", discount)
            if match:
                pct = float(match.group(1))
                if pct > 0:
                    return round(current / (1 - pct / 100), 2)
        return None

    def _extract_discount(
        self, product: dict, price: float, original: Optional[float]
    ) -> Optional[float]:
        for key in ("discount", "discountPercentage", "discountPercent"):
            value = product.get(key)
            if isinstance(value, (int, float)) and value > 0:
                return float(value)
            if isinstance(value, str):
                match = re.search(r"(\d+)", value)
                if match:
                    return float(match.group(1))
        if original and original > price:
            return round((original - price) / original * 100, 1)
        return None

    def _extract_stock(self, product: dict) -> bool:
        for key in ("inStock", "available", "isAvailable"):
            if key in product:
                return bool(product[key])
        stock = product.get("stock") or product.get("stockLevel")
        if isinstance(stock, dict):
            if "inStock" in stock:
                return bool(stock["inStock"])
            level = stock.get("stockLevel") or stock.get("value")
            if isinstance(level, (int, float)):
                return level > 0
        if isinstance(stock, (int, float)):
            return stock > 0
        availability = str(product.get("availability", "")).lower()
        if availability:
            return "out" not in availability and "unavailable" not in availability
        return True

    def _parse_price_value(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, dict):
            for key in ("value", "amount", "raw", "numeric"):
                if key in value:
                    parsed = self._parse_price_value(value[key])
                    if parsed is not None:
                        return parsed
            for key in ("formattedValue", "display", "text"):
                if key in value:
                    parsed = parse_german_price(str(value[key]))
                    if parsed is not None:
                        return parsed
        if isinstance(value, str):
            return parse_german_price(value)
        return None


register_scraper(ZooplusScraper())
