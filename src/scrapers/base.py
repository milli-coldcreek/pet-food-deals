from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Optional
from urllib.parse import urlparse

import requests

from ..models import PriceResult

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 30


def detect_retailer(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "zooplus" in host:
        return "zooplus"
    if "fressnapf" in host:
        return "fressnapf"
    if "zooroyal" in host:
        return "zooroyal"
    raise ValueError(f"Unsupported retailer for URL: {url}")


def parse_german_price(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = text.strip()
    cleaned = cleaned.replace("€", "").replace("EUR", "").strip()
    cleaned = re.sub(r"[^\d,.\-]", "", cleaned)
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


class BaseScraper(ABC):
    retailer: str

    def fetch(self, url: str) -> PriceResult:
        return self.scrape(url)

    @abstractmethod
    def scrape(self, url: str) -> PriceResult:
        raise NotImplementedError


def http_get(url: str, *, headers: Optional[dict] = None) -> requests.Response:
    merged = {"User-Agent": USER_AGENT, "Accept-Language": "de-DE,de;q=0.9"}
    if headers:
        merged.update(headers)
    response = requests.get(url, headers=merged, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response


_SCRAPERS: dict[str, BaseScraper] = {}


def register_scraper(scraper: BaseScraper) -> None:
    _SCRAPERS[scraper.retailer] = scraper


def fetch_price(url: str) -> PriceResult:
    retailer = detect_retailer(url)
    scraper = _SCRAPERS.get(retailer)
    if scraper is None:
        raise ValueError(f"No scraper registered for retailer: {retailer}")
    return scraper.fetch(url)
