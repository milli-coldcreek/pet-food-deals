from .base import detect_retailer, fetch_price
from .fressnapf import FressnapfScraper
from .zooplus import ZooplusScraper
from .zooroyal import ZooroyalScraper

__all__ = [
    "detect_retailer",
    "fetch_price",
    "FressnapfScraper",
    "ZooplusScraper",
    "ZooroyalScraper",
]
