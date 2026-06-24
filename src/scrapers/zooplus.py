from __future__ import annotations

import json
import re
from typing import Any, Optional
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

from ..models import PriceResult
from .base import BaseScraper, http_get, parse_german_price, register_scraper


class ZooplusScraper(BaseScraper):
    retailer = "zooplus"

    def scrape(self, url: str) -> PriceResult:
        response = http_get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        next_data = soup.find("script", id="__NEXT_DATA__")
        if not next_data or not next_data.string:
            raise ValueError("Could not find Zooplus product data on page")

        data = json.loads(next_data.string)
        product = self._extract_product(data)
        if product is None:
            raise ValueError("Could not parse Zooplus product from page data")

        name = product.get("name") or product.get("title") or "Unknown product"
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

    def _extract_product(self, data: Any) -> Optional[dict]:
        candidates = list(self._walk_dicts(data))
        for item in candidates:
            if not isinstance(item, dict):
                continue
            if self._looks_like_product(item):
                return item
        return None

    def _looks_like_product(self, item: dict) -> bool:
        has_name = any(k in item for k in ("name", "title", "productName"))
        has_price = any(k in item for k in ("price", "currentPrice", "offerPrice", "sellingPrice"))
        return has_name and has_price

    def _walk_dicts(self, node: Any):
        if isinstance(node, dict):
            yield node
            for value in node.values():
                yield from self._walk_dicts(value)
        elif isinstance(node, list):
            for value in node:
                yield from self._walk_dicts(value)

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
