from __future__ import annotations

import json
import re
from typing import Any, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from ..models import PriceResult
from .base import BaseScraper, http_get, parse_german_price, register_scraper

PACK_TOTAL_MIN = 3.0
PACK_TOTAL_MAX = 250.0
SINGLE_PACK_MAX = 22.0


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
        name = self._extract_name(soup, data)
        price, original = self._best_pack_price(data, variant_id=variant_id)
        if price is None:
            raise ValueError("Could not parse Zooplus price")

        discount = None
        if original and original > price:
            discount = round((original - price) / original * 100, 1)

        in_stock = True
        product = self._extract_product(data)
        if product is not None:
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

    def _extract_name(self, soup: BeautifulSoup, data: Any) -> str:
        heading = soup.find("h1")
        if heading:
            text = heading.get_text(" ", strip=True)
            if len(text) >= 8:
                return text
        for item in self._walk_dicts(data):
            if not isinstance(item, dict):
                continue
            for key in ("name", "title", "productName"):
                value = item.get(key)
                if isinstance(value, str) and len(value) >= 12:
                    return value
        return "Unknown product"

    def _extract_product(self, data: Any) -> Optional[dict]:
        for item in self._walk_dicts(data):
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

    def _item_related_to_variant(self, item: dict, variant_id: str) -> bool:
        for key in ("articleId", "variantId", "id", "shopIdentifier", "shopArticleId"):
            value = item.get(key)
            if value is not None and str(value) == variant_id:
                return True
        for value in item.values():
            if isinstance(value, (str, int, float)) and str(value) == variant_id:
                return True
        return False

    def _prices_from_item(self, item: dict) -> Tuple[List[float], List[float]]:
        discounted: List[float] = []
        regular: List[float] = []
        for key in ("discountedPriceRaw", "discountPriceRaw"):
            parsed = self._parse_price_value(item.get(key))
            if parsed is not None and PACK_TOTAL_MIN <= parsed <= SINGLE_PACK_MAX:
                discounted.append(parsed)
        for key in ("minArticlePriceRaw", "price", "currentPrice", "offerPrice"):
            parsed = self._parse_price_value(item.get(key))
            if parsed is not None and PACK_TOTAL_MIN <= parsed <= PACK_TOTAL_MAX:
                regular.append(parsed)
        return discounted, regular

    def _best_pack_price(
        self, data: Any, *, variant_id: Optional[str]
    ) -> Tuple[Optional[float], Optional[float]]:
        variant_disc: List[float] = []
        variant_reg: List[float] = []
        all_disc: List[float] = []
        all_reg: List[float] = []

        for item in self._walk_dicts(data):
            if not isinstance(item, dict):
                continue
            discounted, regular = self._prices_from_item(item)
            all_disc.extend(discounted)
            all_reg.extend(regular)
            if variant_id and self._item_related_to_variant(item, variant_id):
                variant_disc.extend(discounted)
                variant_reg.extend(regular)

        if variant_disc:
            price = min(variant_disc)
            original = min(variant_reg) if variant_reg else None
            if original is not None and original <= price:
                original = max(variant_reg) if variant_reg else None
            return price, original or self._pick_original(all_reg, price)

        if variant_reg and variant_id:
            price = min(variant_reg)
            return price, max(variant_reg) if len(variant_reg) > 1 else None

        if all_disc:
            price = min(all_disc)
            return price, self._pick_original(all_reg, price)

        if all_reg:
            price = min(all_reg)
            return price, None

        return None, None

    def _pick_original(self, regular: List[float], current: float) -> Optional[float]:
        above = [p for p in regular if p > current + 0.01]
        return min(above) if above else None

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
