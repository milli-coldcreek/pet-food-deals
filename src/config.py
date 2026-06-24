from __future__ import annotations

import os
from pathlib import Path
from typing import List

import yaml

from .models import DEFAULT_RETAILERS, ProductWatch

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRODUCTS_PATH = ROOT / "products.yaml"


def load_products(path: Path | None = None) -> List[ProductWatch]:
    products_path = path or DEFAULT_PRODUCTS_PATH
    with products_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    products: List[ProductWatch] = []
    for item in data.get("products", []):
        search_query = item.get("search_query") or item.get("query") or item.get("name")
        pack_size = item.get("pack_size", "")
        url = item.get("url")

        retailers = item.get("retailers") or list(DEFAULT_RETAILERS)
        if url and not item.get("search_query"):
            # Legacy URL-only entry: skip search, handled in main via fetch_price
            products.append(
                ProductWatch(
                    name=item["name"],
                    search_query=item["name"],
                    pack_size=pack_size,
                    pet=item.get("pet", ""),
                    target_price=item.get("target_price"),
                    min_discount_pct=float(item.get("min_discount_pct", 10)),
                    retailers=[],
                    url=url,
                )
            )
            continue

        products.append(
            ProductWatch(
                name=item["name"],
                search_query=search_query,
                pack_size=pack_size,
                pet=item.get("pet", ""),
                target_price=item.get("target_price"),
                min_discount_pct=float(item.get("min_discount_pct", 10)),
                retailers=list(retailers),
                retailer_urls=dict(item.get("retailer_urls") or {}),
                url=url,
            )
        )
    return products


def get_telegram_config() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    return token, chat_id
