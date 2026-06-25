from __future__ import annotations

import requests

from .models import DealAlert

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def format_deal_message(alert: DealAlert) -> str:
    product = alert.product
    price = alert.price
    pet_prefix = f"🐾 {product.pet} — " if product.pet else ""

    if alert.kind == "alternative":
        lines = [
            f"{pet_prefix}Variant deal (not your usual product)",
            f"Watching: {product.name} ({product.pack_size})",
        ]
        if alert.primary_price is not None:
            lines.append(
                f"Your usual listing: €{alert.primary_price:.2f} — not on sale right now"
            )
        else:
            lines.append("Your usual listing: not found / not on sale right now")
        lines.append("")
        lines.append(f"Alternative: {price.name}")
        lines.append(f"{price.retailer.capitalize()}: €{price.price:.2f}")
    elif alert.kind == "multipack":
        lines = [
            f"{pet_prefix}Multipack deal (different pack size)",
            f"Watching: {product.name} ({product.pack_size})",
        ]
        if alert.target_unit_price is not None:
            lines.append(f"Your target: €{alert.target_unit_price:.2f}/piece")
        lines.append("")
        lines.append(f"{price.name}")
        lines.append(f"{price.retailer.capitalize()}: €{price.price:.2f} total")
    else:
        lines = [
            f"{pet_prefix}{product.name} ({product.pack_size})",
            f"{price.retailer.capitalize()}: €{price.price:.2f}",
        ]

    if product.target_price is not None and alert.kind == "standard":
        lines.append(f"Target: €{product.target_price:.2f}")

    if alert.unit_price is not None and alert.unit_label:
        lines.append(f"Unit price: €{alert.unit_price:.2f}/piece ({alert.unit_label})")
    if alert.target_unit_price is not None and alert.kind != "standard":
        lines.append(f"Target unit: €{alert.target_unit_price:.2f}/piece")

    if price.original_price and price.original_price > price.price:
        discount = price.discount_pct or round(
            (price.original_price - price.price) / price.original_price * 100, 1
        )
        lines.append(f"(was €{price.original_price:.2f}, -{discount:.0f}%)")
    elif alert.baseline_price and alert.baseline_price > price.price:
        drop = round((alert.baseline_price - price.price) / alert.baseline_price * 100, 1)
        lines.append(f"(baseline €{alert.baseline_price:.2f}, -{drop:.0f}%)")

    lines.append(f"Reason: {alert.reason}")
    if not price.in_stock:
        lines.append("⚠️ Currently out of stock")
    lines.append(price.url)
    return "\n".join(lines)


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
