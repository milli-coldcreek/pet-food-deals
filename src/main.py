from __future__ import annotations

import sys
import time
from pathlib import Path

from .scrapers import fressnapf, zooplus, zooroyal  # noqa: F401

from .config import get_telegram_config, load_products
from .deals import evaluate_alternative_deal, evaluate_deal, evaluate_multipack_deal
from .matching import pack_sizes_match, product_matches
from .notifier import format_deal_message, send_deal_alerts
from .pricing import unit_pricing_from_texts
from .scrapers.base import fetch_price
from .search import search_retailer_full
from .storage import get_product_state, load_state, save_state, update_product_state


def _safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def _url_fallback_ok(url: str, product, matched_name: str = "") -> bool:
    if not url:
        return False
    if (matched_name or "").lower().startswith("suchergebnisse"):
        return False
    if not pack_sizes_match(product.pack_size, url):
        return False
    return product_matches(
        product.search_query,
        product.pack_size,
        matched_name or product.name,
        url=url,
    )


def _try_retailer_url_hint(product, retailer: str) -> "PriceResult | None":
    url = (product.retailer_urls or {}).get(retailer, "").strip()
    if not url or not _url_fallback_ok(url, product):
        return None
    try:
        return fetch_price(url)
    except Exception:
        return None


def _try_url_fallback(product, entry) -> "PriceResult | None":
    url = entry.get("matched_url")
    name = entry.get("matched_name", "")
    if not url:
        return None
    if not _url_fallback_ok(url, product, name):
        entry.pop("matched_url", None)
        entry.pop("matched_name", None)
        return None
    try:
        return fetch_price(url)
    except Exception:
        return None


def run(state_path: Path | None = None, products_path: Path | None = None) -> int:
    products = load_products(products_path)
    if not products:
        print("No products configured in products.yaml")
        return 1

    state = load_state(state_path)
    alerts = []
    errors = 0

    for index, product in enumerate(products):
        if index > 0:
            time.sleep(1)

        if product.url and not product.retailers:
            errors = _check_legacy_url(product, state, alerts, errors)
            continue

        for r_index, retailer in enumerate(product.retailers):
            if r_index > 0:
                time.sleep(1)

            key = product.state_key(retailer)
            entry = get_product_state(state, key)

            try:
                search_result = search_retailer_full(retailer, product)
            except Exception as exc:
                errors += 1
                print(
                    f"ERROR [{product.name} @ {retailer}]: {exc}",
                    file=sys.stderr,
                )
                continue

            price = search_result.primary
            if price is None:
                price = _try_retailer_url_hint(product, retailer)
            if price is None:
                price = _try_url_fallback(product, entry)

            primary_on_deal = False

            if price is None:
                import os

                if os.environ.get("PET_DEAL_DEBUG"):
                    print(
                        f"  DEBUG [{retailer}] no match for {product.search_query!r}",
                        file=sys.stderr,
                    )
                print(
                    f"MISS [{product.name} @ {retailer}] no matching product found "
                    f"(query={product.search_query!r}, pack={product.pack_size!r})"
                )
            else:
                unit = unit_pricing_from_texts(price.price, price.name, price.url)
                unit_note = f" ({unit.price_per_piece:.2f}/pc)" if unit else ""
                print(
                    f"OK  [{product.name} @ {retailer}] €{price.price:.2f}{unit_note} "
                    f"— {price.name[:60]}..."
                )
                entry["matched_url"] = price.url
                entry["matched_name"] = price.name

                alert = _process_price(product, price, entry, state, key)
                if alert:
                    primary_on_deal = True
                    alerts.append(alert)

            primary_price = price.price if price else None
            seen_urls = {
                u.rstrip("/")
                for u in (
                    ([price.url] if price else [])
                    + [a.url for a in search_result.alternatives]
                )
                if u
            }

            for alt in search_result.alternatives:
                unit = unit_pricing_from_texts(alt.price, alt.name, alt.url)
                unit_note = f" ({unit.price_per_piece:.2f}/pc)" if unit else ""
                print(
                    f"ALT [{product.name} @ {retailer}] €{alt.price:.2f}{unit_note} "
                    f"— {alt.name[:55]}..."
                )
                alt_alert = _process_alternative(
                    product,
                    alt,
                    entry,
                    primary_price=primary_price,
                    primary_on_deal=primary_on_deal,
                )
                if alt_alert:
                    alerts.append(alt_alert)

            for mp in search_result.multipacks:
                if mp.url.rstrip("/") in seen_urls:
                    continue
                unit = unit_pricing_from_texts(mp.price, mp.name, mp.url)
                if not unit:
                    continue
                print(
                    f"MPK [{product.name} @ {retailer}] €{mp.price:.2f} "
                    f"({unit.price_per_piece:.2f}/pc, {unit.label}) "
                    f"— {mp.name[:45]}..."
                )
                mp_alert = _process_multipack(
                    product,
                    mp,
                    entry,
                    primary_on_deal=primary_on_deal,
                )
                if mp_alert:
                    alerts.append(mp_alert)

    save_state(state, state_path)

    token, chat_id = get_telegram_config()
    if alerts:
        if token and chat_id:
            sent = send_deal_alerts(token, chat_id, alerts)
            print(f"Sent {sent} Telegram alert(s)")
        else:
            print(
                "Deals found but TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set — "
                "printing alerts:"
            )
            for alert in alerts:
                _safe_print("---")
                _safe_print(format_deal_message(alert))
    else:
        print("No new deals to alert")

    return 1 if errors else 0


def _initial_baseline(price) -> float:
    if price.original_price and price.original_price > price.price:
        return price.original_price
    return price.price


def _process_price(product, price, entry, state, key):
    baseline = entry.get("baseline_price")
    if baseline is None:
        initial_baseline = _initial_baseline(price)
        update_product_state(
            state, key, price=price.price, baseline_price=initial_baseline
        )
        unit = unit_pricing_from_texts(price.price, price.name, price.url)
        if unit:
            entry["baseline_unit_price"] = unit.price_per_piece
        print(f"    Baseline set to €{initial_baseline:.2f}")
        return None

    alert, baseline, alert_price = evaluate_deal(product, price, entry)
    update_product_state(
        state,
        key,
        price=price.price,
        baseline_price=baseline,
        last_alert_price=alert_price if alert else entry.get("last_alert_price"),
    )
    return alert


def _process_alternative(
    product,
    price,
    entry,
    *,
    primary_price: float | None,
    primary_on_deal: bool,
):
    alts = entry.setdefault("alternatives", {})
    alt_entry = alts.setdefault(price.url, {})

    if alt_entry.get("baseline_price") is None:
        initial_baseline = _initial_baseline(price)
        alt_entry["baseline_price"] = initial_baseline
        alt_entry["name"] = price.name
        alt_entry["last_price"] = price.price
        unit = unit_pricing_from_texts(price.price, price.name, price.url)
        if unit:
            alt_entry["baseline_unit_price"] = unit.price_per_piece
        print(f"    Alt baseline set ({price.name[:40]}...): €{initial_baseline:.2f}")
        return None

    alert = evaluate_alternative_deal(
        product,
        price,
        alt_entry,
        primary_price=primary_price,
        primary_on_deal=primary_on_deal,
    )
    alt_entry["last_price"] = price.price
    if alert:
        alt_entry["last_alert_price"] = price.price
    return alert


def _process_multipack(
    product,
    price,
    entry,
    *,
    primary_on_deal: bool,
):
    packs = entry.setdefault("multipacks", {})
    mp_entry = packs.setdefault(price.url, {})

    unit = unit_pricing_from_texts(price.price, price.name, price.url)
    if unit is None:
        return None

    if mp_entry.get("baseline_unit_price") is None:
        mp_entry["baseline_price"] = price.price
        mp_entry["baseline_unit_price"] = unit.price_per_piece
        mp_entry["name"] = price.name
        mp_entry["pack_label"] = unit.label
        mp_entry["last_price"] = price.price
        print(
            f"    Multipack baseline ({unit.label}): "
            f"€{unit.price_per_piece:.2f}/piece"
        )
        return None

    alert = evaluate_multipack_deal(
        product,
        price,
        mp_entry,
        primary_on_deal=primary_on_deal,
    )
    mp_entry["last_price"] = price.price
    if alert:
        mp_entry["last_alert_unit_price"] = unit.price_per_piece
    return alert


def _check_legacy_url(product, state, alerts, errors):
    key = product.url.strip().rstrip("/") if product.url else product.key
    entry = get_product_state(state, key)
    try:
        price = fetch_price(product.url)
    except Exception as exc:
        print(f"ERROR [{product.name}]: {exc}", file=sys.stderr)
        return errors + 1

    print(f"OK  [{product.name}] €{price.price:.2f} ({price.retailer})")
    alert = _process_price(product, price, entry, state, key)
    if alert:
        alerts.append(alert)
    return errors


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
