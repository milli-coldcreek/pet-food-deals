from __future__ import annotations

import json
import re
from typing import Any, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from ..matching import parse_pack_size
from ..models import PriceResult
from .base import BaseScraper, http_get, parse_german_price, register_scraper

PACK_TOTAL_MIN = 3.0
PACK_TOTAL_MAX = 250.0

MIN_UNIT_EUR: dict[tuple[str, int], float] = {
    ("g", 85): 0.75,
    # Allow deep Extra-Rabatt (e.g. Feringa 24× €32.19 ≈ €1.34/pc)
    ("g", 400): 1.20,
    ("g", 800): 1.80,
}

SUBSCRIPTION_KEY_HINTS = (
    "abo",
    "subscription",
    "autoship",
    "autoshipment",
    "recurring",
    "repeat",
    "recurrence",
    "sparabo",
    "zooplusabo",
)
MIN_TRUSTED_DISCOUNT_RATIO = 0.70

PRICE_VALUE_RE = re.compile(
    r'"([^"]*(?:price|Price)[^"]*)"\s*:\s*(\d+(?:\.\d+)?)',
)

EINZEL_BLOCK_RE = re.compile(
    r"Einzellieferung.{0,120}?(\d{1,3}[,.]\d{2})\s*€.{0,80}?(\d{1,3}[,.]\d{2})\s*€",
    re.IGNORECASE | re.DOTALL,
)

EXTRA_RABATT_PCT_RE = re.compile(
    r"(-?\d+)\s*%\s*Extra-Rabatt",
    re.IGNORECASE,
)

# Also matches "Aktiviert -30% Rabatt im Warenkorb"
ACTIVATED_RABATT_PCT_RE = re.compile(
    r"Aktiviert\s*(-?\d+)\s*%\s*Rabatt",
    re.IGNORECASE,
)

EINZEL_SINGLE_RE = re.compile(
    r"Einzellieferung.{0,80}?(\d{1,3}[,.]\d{2})\s*€",
    re.IGNORECASE | re.DOTALL,
)

DISCOUNTED_RAW_RE = re.compile(r'"discountedPriceRaw"\s*:\s*(\d+)')

ABO_JSON_CONTEXT_RE = re.compile(
    r'"zooplusAbo"|"zooplusABO"|"subscriptionOffer"|"subscriptionPrice"|"sparAbo"|"autoshipment"',
    re.IGNORECASE,
)

# Zooplus Abo is typically exactly 10% below list — same as Einzellieferung, so never
# trust JSON-only 10% discounts; use HTML Einzellieferung / Extra-Rabatt blocks instead.
STANDARD_ABO_DISCOUNT_PCT = 10.0
PRICE_MATCH_TOLERANCE = 0.02


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
        price, original = self._resolve_price(
            data, soup=soup, variant_id=variant_id, name=name, url=url
        )
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
        has_price = any(self._is_price_field(k) for k in item)
        return has_name and has_price

    def _walk_dicts(self, node: Any):
        if isinstance(node, dict):
            yield node
            for value in node.values():
                yield from self._walk_dicts(value)
        elif isinstance(node, list):
            for value in node:
                yield from self._walk_dicts(value)

    def _is_price_field(self, key: str) -> bool:
        return "price" in key.lower()

    def _is_subscription_price_field(self, key: str) -> bool:
        lowered = key.lower()
        return any(hint in lowered for hint in SUBSCRIPTION_KEY_HINTS)

    def _variant_matches(self, item: dict, variant_id: str) -> bool:
        for key in ("articleId", "shopArticleId", "id", "variantId", "activeVariant"):
            value = item.get(key)
            if value is not None and str(value) == variant_id:
                return True
        return False

    def _extract_prices_from_node(
        self, node: dict, *, depth: int = 0, in_subscription_branch: bool = False
    ) -> dict[str, Any]:
        found: dict[str, Any] = {}
        if depth > 3 or in_subscription_branch:
            return found
        for key, value in node.items():
            if self._is_subscription_price_field(key):
                continue
            if self._is_price_field(key):
                found[key] = value
                continue
            if isinstance(value, dict):
                child_is_sub = self._is_subscription_price_field(key) or key.lower() in (
                    "zooplusabo",
                    "subscription",
                    "abooptions",
                    "autoshipment",
                )
                for sub_key, sub_value in value.items():
                    if self._is_subscription_price_field(sub_key) or child_is_sub:
                        continue
                    if self._is_price_field(sub_key):
                        found[sub_key] = sub_value
                nested = self._extract_prices_from_node(
                    value, depth=depth + 1, in_subscription_branch=child_is_sub
                )
                for sub_key, sub_value in nested.items():
                    if sub_key not in found:
                        found[sub_key] = sub_value
        return found

    def _active_variant_prices(self, data: Any, variant_id: str) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for item in self._walk_dicts(data):
            if not isinstance(item, dict):
                continue
            for av_key in (
                "activeVariant",
                "selectedVariant",
                "selectedArticleId",
                "activeArticleId",
            ):
                if str(item.get(av_key, "")) != variant_id:
                    continue
                for key, value in self._extract_prices_from_node(item).items():
                    if key not in merged:
                        merged[key] = value
        return merged

    def _merged_variant_article(self, data: Any, variant_id: str) -> dict:
        merged: dict[str, Any] = {}
        for item in self._walk_dicts(data):
            if not isinstance(item, dict):
                continue
            if self._variant_matches(item, variant_id):
                for key, value in self._extract_prices_from_node(item).items():
                    if key not in merged:
                        merged[key] = value
            for key, value in item.items():
                if str(key) == variant_id and isinstance(value, dict):
                    for pkey, pvalue in self._extract_prices_from_node(value).items():
                        if pkey not in merged:
                            merged[pkey] = pvalue
        merged.update(self._active_variant_prices(data, variant_id))
        merged.update(self._regex_prices_near_variant(data, variant_id))
        return merged

    def _regex_prices_near_variant(self, data: Any, variant_id: str) -> dict[str, Any]:
        text = json.dumps(data, ensure_ascii=False)
        fields: dict[str, Any] = {}
        for anchor in (f'"{variant_id}"', f'"articleId":"{variant_id}"'):
            start = 0
            while True:
                idx = text.find(anchor, start)
                if idx < 0:
                    break
                chunk = text[max(0, idx - 800) : idx + 3000]
                if self._json_chunk_is_abo_context(chunk):
                    start = idx + len(anchor)
                    continue
                for match in PRICE_VALUE_RE.finditer(chunk):
                    key, raw = match.group(1), match.group(2)
                    if self._is_subscription_price_field(key):
                        continue
                    if key in fields:
                        continue
                    fields[key] = int(raw) if raw.isdigit() else float(raw)
                start = idx + len(anchor)
        return fields

    def _json_chunk_is_abo_context(self, chunk: str) -> bool:
        return bool(ABO_JSON_CONTEXT_RE.search(chunk))

    def _is_standard_abo_price(self, price: float, list_price: Optional[float]) -> bool:
        if list_price is None or list_price <= 0:
            return False
        expected = round(list_price * (1 - STANDARD_ABO_DISCOUNT_PCT / 100), 2)
        return abs(price - expected) <= PRICE_MATCH_TOLERANCE

    def _html_verified_discounts(
        self, soup: BeautifulSoup, list_price: Optional[float]
    ) -> list[Tuple[float, Optional[float]]]:
        """Only Extra-Rabatt counts as a one-time discount.

        Einzellieferung -10% matches zooplus Abo -10% on many products and causes
        false alerts for Feringa/Cosma. Extra-Rabatt (-20%/-30%) is the real sale
        tier (e.g. Royal Canin €12.39, Feringa €32.19).
        """
        verified: list[Tuple[float, Optional[float]]] = []
        text = soup.get_text(" ", strip=True)
        lowered = text.lower()
        if "extra-rabatt" not in lowered and "rabatt im warenkorb" not in lowered:
            return verified

        extra_price, extra_regular = self._extra_rabatt_price(soup, list_price)
        if extra_price is not None:
            verified.append((extra_price, extra_regular))

        # When Extra-Rabatt is activated, Einzellieferung already shows cart price.
        pct = self._extra_rabatt_pct(text)
        einzel_disc, einzel_reg = self._einzel_delivery_price(soup)
        if pct is not None and einzel_disc is not None and einzel_reg is not None:
            expected = round(einzel_reg * (1 - pct / 100), 2)
            if abs(expected - einzel_disc) <= PRICE_MATCH_TOLERANCE:
                verified.append((einzel_disc, einzel_reg))
        return verified

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
        minimum = self._min_plausible_total(name, url)
        if minimum is not None and price < minimum:
            return False
        return PACK_TOTAL_MIN <= price <= PACK_TOTAL_MAX

    def _is_list_price_key(self, key: str) -> bool:
        lowered = key.lower()
        if self._is_subscription_price_field(key):
            return False
        if "discount" in lowered:
            return False
        return any(
            token in lowered
            for token in ("minarticleprice", "listprice", "articleprice", "sellingprice")
        )

    def _is_one_time_discount_key(self, key: str) -> bool:
        if self._is_subscription_price_field(key):
            return False
        lowered = key.lower()
        if "discount" in lowered:
            return True
        return lowered in {"offerprice", "offerpriceraw", "reducedprice", "specialprice"}

    def _list_price_from_article(self, article: dict) -> Optional[float]:
        values: list[float] = []
        for key, value in article.items():
            if not self._is_list_price_key(key):
                continue
            parsed = self._parse_price_value(value)
            if parsed is not None:
                values.append(parsed)
        return max(values) if values else None

    def _trusted_discount(
        self, discounted: float, list_price: Optional[float]
    ) -> bool:
        if list_price is None or list_price <= 0:
            return True
        if discounted >= list_price:
            return False
        # Allow exact -30% after euro rounding (e.g. 45.99 → 32.19).
        floor = list_price * MIN_TRUSTED_DISCOUNT_RATIO
        return discounted + PRICE_MATCH_TOLERANCE >= floor

    def _one_time_deals_from_article(
        self, article: dict, list_price: Optional[float]
    ) -> list[Tuple[float, Optional[float]]]:
        """Legacy helper for tests — JSON discount fields are not trusted alone."""
        deals: list[Tuple[float, Optional[float]]] = []
        seen_prices: set[float] = set()

        for key, value in article.items():
            if not self._is_one_time_discount_key(key):
                continue
            parsed = self._parse_price_value(value)
            if parsed is None or parsed in seen_prices:
                continue
            if list_price is not None and self._is_standard_abo_price(parsed, list_price):
                continue
            if not self._trusted_discount(parsed, list_price):
                continue
            seen_prices.add(parsed)
            original = list_price if list_price and parsed < list_price else None
            deals.append((parsed, original))
        return deals

    def _page_text_before_abo(self, soup: BeautifulSoup) -> str:
        text = soup.get_text(" ", strip=True)
        return re.split(r"zooplus\s+Abo", text, maxsplit=1, flags=re.IGNORECASE)[0]

    def _extra_rabatt_pct(self, text: str) -> Optional[int]:
        match = EXTRA_RABATT_PCT_RE.search(text)
        if match:
            pct = abs(int(match.group(1)))
            if 5 <= pct <= 50:
                return pct
        match = ACTIVATED_RABATT_PCT_RE.search(text)
        if match:
            pct = abs(int(match.group(1)))
            if 5 <= pct <= 50:
                return pct
        if not re.search(r"extra-rabatt|rabatt im warenkorb", text, re.IGNORECASE):
            return None
        for match in re.finditer(r"(-?\d+)\s*%", text):
            pos = match.start()
            context = text[max(0, pos - 100) : pos + 100]
            if not re.search(
                r"extra-rabatt|rabatt im warenkorb", context, re.IGNORECASE
            ):
                continue
            pct = abs(int(match.group(1)))
            if 5 <= pct <= 50:
                return pct
        return None

    def _einzel_one_time_base(self, soup: BeautifulSoup) -> Optional[float]:
        """Einzellieferung sticker price Extra-Rabatt is applied to (e.g. €45.99)."""
        discounted, regular = self._einzel_delivery_price(soup)
        if regular is not None:
            return regular
        if discounted is not None:
            return discounted
        for node in soup.find_all(string=re.compile(r"Einzellieferung", re.IGNORECASE)):
            parent = node.parent
            for _ in range(8):
                if parent is None:
                    break
                block = parent.get_text(" ", strip=True)
                if "zooplus abo" in block.lower():
                    break
                match = EINZEL_SINGLE_RE.search(block)
                if match:
                    return parse_german_price(match.group(1))
                parent = parent.parent
        return None

    def _infer_list_price(
        self,
        article: dict,
        *,
        soup: BeautifulSoup,
        data: Any,
        variant_id: str,
    ) -> Optional[float]:
        list_price = self._list_price_from_article(article) if article else None
        if list_price is not None:
            return list_price

        _, regular = self._einzel_delivery_price(soup)
        if regular is not None:
            return regular

        for key, raw in self._regex_prices_near_variant(data, variant_id).items():
            if not self._is_list_price_key(key):
                continue
            parsed = self._parse_price_value(raw)
            if parsed is not None:
                return parsed
        return None

    def _extra_rabatt_price(
        self, soup: BeautifulSoup, list_price: Optional[float]
    ) -> Tuple[Optional[float], Optional[float]]:
        """Zooplus Extra-Rabatt before/after activation (e.g. -30% of €45.99 → €32.19).

        Apply % to the Einzellieferung offer when available — not the higher
        "Einzeln" comparison price (49.96), which would understate the discount.
        """
        text = soup.get_text(" ", strip=True)
        if (
            "extra-rabatt" not in text.lower()
            and "rabatt im warenkorb" not in text.lower()
        ):
            return None, None

        pct = self._extra_rabatt_pct(text)
        if pct is None:
            pct = self._extra_rabatt_pct(str(soup))
        if pct is None:
            return None, None

        bases: list[float] = []
        for candidate in (self._einzel_one_time_base(soup), list_price):
            if candidate is not None and candidate not in bases:
                bases.append(candidate)
        if not bases:
            return None, None

        best: Optional[Tuple[float, float]] = None
        for base in bases:
            discounted = round(base * (1 - pct / 100), 2)
            if discounted >= base:
                continue
            if not self._trusted_discount(discounted, base):
                continue
            if best is None or discounted < best[0]:
                best = (discounted, base)
        if best is None:
            return None, None
        return best

    def _json_discounted_prices(
        self, data: Any, variant_id: str, list_price: Optional[float]
    ) -> list[Tuple[float, Optional[float]]]:
        deals: list[Tuple[float, Optional[float]]] = []
        seen: set[float] = set()
        blob = json.dumps(data, ensure_ascii=False)
        for match in DISCOUNTED_RAW_RE.finditer(blob):
            chunk = blob[max(0, match.start() - 1500) : match.end() + 500]
            if variant_id not in chunk and f'"articleId":"{variant_id}"' not in chunk:
                continue
            if self._json_chunk_is_abo_context(chunk):
                continue
            parsed = self._parse_price_value(int(match.group(1)))
            if parsed is None or parsed in seen:
                continue
            if list_price is not None and self._is_standard_abo_price(parsed, list_price):
                continue
            if list_price is not None and not self._trusted_discount(parsed, list_price):
                continue
            seen.add(parsed)
            original = list_price if list_price and parsed < list_price else None
            deals.append((parsed, original))
        return deals

    def _einzel_delivery_price(
        self, soup: BeautifulSoup
    ) -> Tuple[Optional[float], Optional[float]]:
        for node in soup.find_all(string=re.compile(r"Einzellieferung", re.IGNORECASE)):
            parent = node.parent
            for _ in range(8):
                if parent is None:
                    break
                block = parent.get_text(" ", strip=True)
                if "zooplus abo" in block.lower():
                    break
                match = EINZEL_BLOCK_RE.search(block)
                if match:
                    regular = parse_german_price(match.group(1))
                    discounted = parse_german_price(match.group(2))
                    if (
                        regular is not None
                        and discounted is not None
                        and discounted < regular
                    ):
                        return discounted, regular
                parent = parent.parent
        return None, None

    def _resolve_price(
        self,
        data: Any,
        *,
        soup: BeautifulSoup,
        variant_id: Optional[str],
        name: str,
        url: str,
    ) -> Tuple[Optional[float], Optional[float]]:
        if not variant_id:
            return None, None

        article = self._merged_variant_article(data, variant_id)
        list_price = self._infer_list_price(
            article, soup=soup, data=data, variant_id=variant_id
        )

        candidates: list[Tuple[float, Optional[float]]] = []

        if list_price is not None and self._price_plausible(list_price, name, url):
            candidates.append((list_price, None))

        for deal_price, deal_original in self._html_verified_discounts(soup, list_price):
            if self._price_plausible(deal_price, name, url):
                candidates.append((deal_price, deal_original))

        if not candidates:
            return None, None

        best_price, best_original = min(candidates, key=lambda row: row[0])
        if list_price is not None and self._is_standard_abo_price(best_price, list_price):
            return list_price, None
        if (
            best_original is not None
            and best_price >= best_original
            and list_price is not None
            and best_price < list_price
        ):
            best_original = list_price
        return best_price, best_original

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
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            if value >= 100:
                return value / 100.0
            return float(value)
        if isinstance(value, float):
            return value
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
