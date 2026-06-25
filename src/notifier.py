from __future__ import annotations

import requests

from .models import DealAlert

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def format_deal_message(alert: DealAlert) -> str:
    product = alert.product
    price = alert.price
    pet = product.pet or "Pet"
    title = f"{pet} — {product.name}"
    deal_price = f"€{price.price:.2f}"
    if not price.in_stock:
        deal_price = f"{deal_price} (out of stock)"

    return "\n".join([title, deal_price, price.url])


def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    url = TELEGRAM_API.format(token=token)
    try:
        response = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": False},
            timeout=30,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status == 404:
            raise RuntimeError(
                "Telegram rejected the bot token (HTTP 404). "
                "Check TELEGRAM_BOT_TOKEN from @BotFather — do not use the README placeholder."
            ) from exc
        if status == 401:
            raise RuntimeError(
                "Telegram rejected the bot token (HTTP 401). "
                "Regenerate the token with @BotFather if needed."
            ) from exc
        raise RuntimeError(f"Telegram HTTP error {status}: {exc}") from exc
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API error: {payload}")


def send_deal_alerts(token: str, chat_id: str, alerts: list[DealAlert]) -> int:
    sent = 0
    for alert in alerts:
        send_telegram_message(token, chat_id, format_deal_message(alert))
        sent += 1
    return sent
