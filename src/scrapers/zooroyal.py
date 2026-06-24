from __future__ import annotations

import json
import re
from typing import Any, Optional

from bs4 import BeautifulSoup

from ..models import PriceResult
from .base import BaseScraper, http_get, parse_german_price, register_scraper


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
        price, original, discount = self._extract_from_html(soup)
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
        if isinstance(data, dict):
            if data.get("@type") == "Product":
                return data
            graph = data.get("@graph")
            if isinstance(graph, list):
                return self._find_product_ld(graph)
        return None

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
        html_price, original, discount = self._extract_from_html(soup)
        if price is None:
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
            original_price=original,
            discount_pct=discount,
            in_stock=in_stock,
        )

    def _extract_from_html(
        self, soup: BeautifulSoup
    ) -> tuple[Optional[float], Optional[float], Optional[float]]:
        text = soup.get_text(" ", strip=True)

        price = None
        original = None
        discount = None

        # Prefer price near "In den Warenkorb" (active variant selection).
        cart_idx = text.lower().find("in den warenkorb")
        search_text = text[max(0, cart_idx - 120) : cart_idx] if cart_idx > 0 else text
        price_match = re.search(r"(\d+[,.]\d{2})\s*€", search_text)
        if price_match:
            price = parse_german_price(price_match.group(1))
        elif not price:
            fallback = re.search(r"(\d+[,.]\d{2})\s*€", text)
            if fallback:
                price = parse_german_price(fallback.group(1))

        uvp_match = re.search(r"UVP\s*([\d.,]+)\s*€", text, re.IGNORECASE)
        if uvp_match:
            original = parse_german_price(uvp_match.group(1))

        discount_match = re.search(r"-\s*(\d+)\s*%", text)
        if discount_match:
            discount = float(discount_match.group(1))

        if original and price and original > price and discount is None:
            discount = round((original - price) / original * 100, 1)

        meta = soup.find("meta", property="product:price:amount")
        if meta and meta.get("content"):
            meta_price = parse_german_price(meta["content"])
            if meta_price is not None:
                price = meta_price

        return price, original, discount


register_scraper(ZooroyalScraper())
