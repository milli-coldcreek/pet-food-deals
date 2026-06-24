from __future__ import annotations

import json
import re
from typing import Any, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from ..models import PriceResult
from .base import BaseScraper, http_get, parse_german_price, register_scraper

API_BASE = "https://api.os.fressnapf.com/rest/v2/fressnapfDE"


class FressnapfScraper(BaseScraper):
    retailer = "fressnapf"

    def scrape(self, url: str) -> PriceResult:
        product_code = self._extract_product_code(url)
        if product_code:
            try:
                return self._scrape_via_api(url, product_code)
            except Exception:
                pass
        return self._scrape_via_html(url)

    def _extract_product_code(self, url: str) -> Optional[str]:
        path = urlparse(url).path.strip("/")
        segments = [s for s in path.split("/") if s]
        for segment in reversed(segments):
            if re.fullmatch(r"\d{5,}", segment):
                return segment
        match = re.search(r"/p/(\d+)", url)
        if match:
            return match.group(1)
        return None

    def _scrape_via_api(self, url: str, product_code: str) -> PriceResult:
        api_url = f"{API_BASE}/products/{product_code}?fields=FULL"
        response = http_get(api_url, headers={"Accept": "application/json"})
        data = response.json()
        return self._parse_api_product(data, url)

    def _parse_api_product(self, data: dict, url: str) -> PriceResult:
        name = data.get("name") or data.get("summary") or "Unknown product"
        price = self._extract_product_price(data)
        if price is None:
            raise ValueError("Could not parse Fressnapf API price")

        original = None
        for key in ("wasPrice", "oldPrice", "strikeThroughPrice"):
            original = self._parse_price_info(data.get(key))
            if original is not None and original > price:
                break
            original = None

        discount = None
        if original and original > price:
            discount = round((original - price) / original * 100, 1)

        stock = data.get("stock", {})
        in_stock = True
        if isinstance(stock, dict):
            level = stock.get("stockLevel")
            if isinstance(level, (int, float)):
                in_stock = level > 0
        if "availableForPickup" in data:
            in_stock = bool(data.get("purchasable", True))

        return PriceResult(
            name=name,
            price=price,
            url=url,
            retailer=self.retailer,
            original_price=original,
            discount_pct=discount,
            in_stock=in_stock,
        )

    def _parse_price_info(self, price_info: Any) -> Optional[float]:
        if price_info is None:
            return None
        if isinstance(price_info, (int, float)):
            return float(price_info)
        if isinstance(price_info, dict):
            if "value" in price_info and price_info["value"] is not None:
                return float(price_info["value"])
            if "formattedValue" in price_info:
                return parse_german_price(str(price_info["formattedValue"]))
        if isinstance(price_info, str):
            return parse_german_price(price_info)
        return None

    def _extract_product_price(self, data: dict) -> Optional[float]:
        pricing = data.get("pricing") or {}
        if isinstance(pricing, dict):
            current = pricing.get("current")
            if isinstance(current, dict):
                parsed = self._parse_price_info(current)
                if parsed is not None:
                    return parsed

        parsed = self._parse_price_info(data.get("price"))
        if parsed is not None:
            return parsed

        price_range = data.get("priceRange") or {}
        if isinstance(price_range, dict):
            for key in ("minPrice", "maxPrice"):
                parsed = self._parse_price_info(price_range.get(key))
                if parsed is not None:
                    return parsed

        volume_prices = data.get("volumePrices") or []
        if isinstance(volume_prices, list):
            values = [
                self._parse_price_info(entry)
                for entry in volume_prices
                if isinstance(entry, dict)
            ]
            values = [v for v in values if v is not None]
            if values:
                return min(values)

        return None

    def _scrape_via_html(self, url: str) -> PriceResult:
        response = http_get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except json.JSONDecodeError:
                continue
            product = self._find_product_ld(data)
            if product:
                return self._parse_ld_product(product, url)

        title = soup.find("h1")
        name = title.get_text(strip=True) if title else "Unknown product"
        price = self._extract_price_from_html(soup)
        if price is None:
            raise ValueError("Could not parse Fressnapf price from HTML")

        original = self._extract_original_from_html(soup, price)
        discount = None
        if original and original > price:
            discount = round((original - price) / original * 100, 1)

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

    def _parse_ld_product(self, product: dict, url: str) -> PriceResult:
        name = product.get("name", "Unknown product")
        offers = product.get("offers")
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if not isinstance(offers, dict):
            offers = {}

        price = parse_german_price(str(offers.get("price", "")))
        if price is None:
            raise ValueError("Could not parse Fressnapf JSON-LD price")

        availability = str(offers.get("availability", "")).lower()
        in_stock = "outofstock" not in availability

        return PriceResult(
            name=name,
            price=price,
            url=url,
            retailer=self.retailer,
            in_stock=in_stock,
        )

    def _extract_price_from_html(self, soup: BeautifulSoup) -> Optional[float]:
        meta = soup.find("meta", property="product:price:amount")
        if meta and meta.get("content"):
            return parse_german_price(meta["content"])

        for pattern in (
            r'"price"\s*:\s*"?([\d.,]+)"?',
            r'"value"\s*:\s*([\d.]+)',
            r'class="[^"]*price[^"]*"[^>]*>([^<]+)<',
        ):
            match = re.search(pattern, soup.get_text(" ", strip=True), re.IGNORECASE)
            if match:
                parsed = parse_german_price(match.group(1))
                if parsed is not None:
                    return parsed
        return None

    def _extract_original_from_html(
        self, soup: BeautifulSoup, current: float
    ) -> Optional[float]:
        text = soup.get_text(" ", strip=True)
        match = re.search(
            r"(?:UVP|statt|ursprünglich|vorher)\s*[:\s]*([\d.,]+)\s*€",
            text,
            re.IGNORECASE,
        )
        if match:
            original = parse_german_price(match.group(1))
            if original and original > current:
                return original
        return None


register_scraper(FressnapfScraper())
