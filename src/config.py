from __future__ import annotations

import os
from pathlib import Path
from typing import List

import yaml

from .models import DEFAULT_RETAILERS, ProductWatch

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRODUCTS_PATH = ROOT / "products.yaml"
_DOTENV_LOADED = False

_PLACEHOLDER_TOKENS = frozenset(
    {
        "your-bot-token",
        "your-token",
        "your_token",
        "your-chat-id",
        "your-chat-id-here",
        "<token>",
        "<chat_id>",
        "xxx",
    }
)


def _load_dotenv() -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def telegram_config_error(token: str, chat_id: str) -> str | None:
    """Return a user-facing error when Telegram env vars look wrong."""
    if not token or not chat_id:
        return None
    if token.lower() in _PLACEHOLDER_TOKENS:
        return (
            "TELEGRAM_BOT_TOKEN is still a placeholder — paste your real token from "
            "@BotFather into .env or $env:TELEGRAM_BOT_TOKEN"
        )
    if chat_id.lower() in _PLACEHOLDER_TOKENS:
        return (
            "TELEGRAM_CHAT_ID is still a placeholder — use your numeric chat id from "
            "getUpdates"
        )
    if ":" not in token:
        return (
            "TELEGRAM_BOT_TOKEN does not look valid (expected format like "
            "123456789:AAH... from @BotFather)"
        )
    if not chat_id.lstrip("-").isdigit():
        return "TELEGRAM_CHAT_ID should be a numeric id (e.g. 1446985649)"
    return None


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
    _load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    return token, chat_id
