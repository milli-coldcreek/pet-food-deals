from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .models import DealAlert, PriceResult, ProductWatch
from .pricing import format_unit_price, target_unit_price, unit_pricing_from_texts

# Ignore single-check drops steeper than this — usually a scrape mismatch.
MAX_TRUSTED_DROP_PCT = 35.0


def _trusted_price_drop(baseline: Optional[float], price: float) -> bool:
    if baseline is None or baseline <= 0 or price >= baseline:
        return True
    drop_pct = (baseline - price) / baseline * 100
    return drop_pct <= MAX_TRUSTED_DROP_PCT


def _trusted_unit_drop(baseline_unit: Optional[float], unit_price: float) -> bool:
    if baseline_unit is None or baseline_unit <= 0 or unit_price >= baseline_unit:
        return True
    drop_pct = (baseline_unit - unit_price) / baseline_unit * 100
    return drop_pct <= MAX_TRUSTED_DROP_PCT


def _listing_unit(price: PriceResult) -> Optional[tuple[float, str]]:
    unit = unit_pricing_from_texts(price.price, price.name, price.url)
    if unit is None:
        return None
    return unit.price_per_piece, unit.label


def _unit_target(product: ProductWatch) -> Optional[float]:
    if product.target_price is None:
        return None
    return target_unit_price(product.target_price, product.pack_size)


def _unit_deal_reasons(
    product: ProductWatch,
    price: PriceResult,
    *,
    baseline_unit: Optional[float],
) -> List[str]:
    reasons: List[str] = []
    listing = unit_pricing_from_texts(price.price, price.name, price.url)
    if listing is None:
        return reasons

    target_unit = _unit_target(product)
    if target_unit is not None and listing.price_per_piece <= target_unit:
        reasons.append(
            f"{format_unit_price(listing)} ≤ target €{target_unit:.2f}/piece"
        )

    if baseline_unit and baseline_unit > 0:
        drop = (baseline_unit - listing.price_per_piece) / baseline_unit * 100
        if drop >= product.min_discount_pct:
            reasons.append(
                f"{drop:.0f}% below unit baseline (€{baseline_unit:.2f}/piece)"
            )

    return reasons


def evaluate_deal(
    product: ProductWatch,
    price: PriceResult,
    product_state: Dict[str, Any],
    *,
    force_alert: bool = False,
) -> Tuple[Optional[DealAlert], float, Optional[float]]:
    """Return (alert_or_none, new_baseline, alert_price_if_sent)."""
    baseline = product_state.get("baseline_price")
    baseline_unit = product_state.get("baseline_unit_price")
    last_alert_price = (
        None if force_alert else product_state.get("last_alert_price")
    )

    listing = unit_pricing_from_texts(price.price, price.name, price.url)

    if baseline is None:
        return None, price.price, None

    reasons: List[str] = []

    if product.target_price is not None and price.price <= product.target_price:
        reasons.append(f"at or below target €{product.target_price:.2f}")

    drop_pct = (baseline - price.price) / baseline * 100 if baseline > 0 else 0
    if drop_pct >= product.min_discount_pct:
        reasons.append(f"{drop_pct:.0f}% below baseline (€{baseline:.2f})")

    if (
        price.original_price
        and price.original_price > price.price
        and price.price < baseline
    ):
        sale_pct = price.discount_pct or round(
            (price.original_price - price.price) / price.original_price * 100, 1
        )
        if sale_pct >= product.min_discount_pct:
            reasons.append(f"retailer sale ({sale_pct:.0f}% off UVP)")

    reasons.extend(
        _unit_deal_reasons(product, price, baseline_unit=baseline_unit)
    )

    if not reasons:
        return None, baseline, None

    if not _trusted_price_drop(baseline, price.price):
        return None, baseline, None

    if last_alert_price is not None and abs(last_alert_price - price.price) < 0.01:
        return None, baseline, None

    unit_piece, unit_label = _listing_unit(price) or (None, None)
    alert = DealAlert(
        product=product,
        price=price,
        reason="; ".join(dict.fromkeys(reasons)),
        baseline_price=baseline,
        unit_price=unit_piece,
        unit_label=unit_label,
        target_unit_price=_unit_target(product),
    )
    return alert, baseline, price.price


def deal_suppressed_reason(
    product: ProductWatch,
    price: PriceResult,
    product_state: Dict[str, Any],
) -> Optional[str]:
    """Explain why a qualifying deal did not alert (usually anti-spam)."""
    alert, _, _ = evaluate_deal(product, price, product_state)
    if alert is not None:
        return None

    last_alert = product_state.get("last_alert_price")
    if last_alert is None:
        return None

    without_spam = dict(product_state)
    without_spam.pop("last_alert_price", None)
    would_alert, _, _ = evaluate_deal(product, price, without_spam)
    if would_alert is None:
        return None

    return f"already notified at €{last_alert:.2f}"


def evaluate_alternative_deal(
    product: ProductWatch,
    price: PriceResult,
    alt_state: Dict[str, Any],
    *,
    primary_price: Optional[float],
    primary_on_deal: bool,
) -> Optional[DealAlert]:
    """Alert on seasonal/limited variants when the usual listing is not a deal."""
    if primary_on_deal:
        return None

    baseline = alt_state.get("baseline_price")
    baseline_unit = alt_state.get("baseline_unit_price")
    last_alert_price = alt_state.get("last_alert_price")

    if baseline is None:
        return None

    reasons: List[str] = []

    if product.target_price is not None and price.price <= product.target_price:
        reasons.append(f"at or below target €{product.target_price:.2f}")

    drop_pct = (baseline - price.price) / baseline * 100 if baseline > 0 else 0
    if drop_pct >= product.min_discount_pct:
        reasons.append(f"{drop_pct:.0f}% below this variant's baseline (€{baseline:.2f})")

    if (
        price.original_price
        and price.original_price > price.price
        and price.price < baseline
    ):
        sale_pct = price.discount_pct or round(
            (price.original_price - price.price) / price.original_price * 100, 1
        )
        if sale_pct >= product.min_discount_pct:
            reasons.append(f"retailer sale ({sale_pct:.0f}% off UVP)")

    reasons.extend(
        _unit_deal_reasons(product, price, baseline_unit=baseline_unit)
    )

    if not reasons:
        return None

    if not _trusted_price_drop(baseline, price.price):
        return None

    if last_alert_price is not None and abs(last_alert_price - price.price) < 0.01:
        return None

    unit_piece, unit_label = _listing_unit(price) or (None, None)
    return DealAlert(
        product=product,
        price=price,
        reason="; ".join(dict.fromkeys(reasons)),
        baseline_price=baseline,
        kind="alternative",
        primary_price=primary_price,
        unit_price=unit_piece,
        unit_label=unit_label,
        target_unit_price=_unit_target(product),
    )


def evaluate_multipack_deal(
    product: ProductWatch,
    price: PriceResult,
    mp_state: Dict[str, Any],
    *,
    primary_on_deal: bool,
) -> Optional[DealAlert]:
    """Alert when a larger/smaller multipack is cheap per piece."""
    if primary_on_deal:
        return None

    listing = unit_pricing_from_texts(price.price, price.name, price.url)
    if listing is None:
        return None

    baseline_unit = mp_state.get("baseline_unit_price")
    last_alert_unit = mp_state.get("last_alert_unit_price")

    if baseline_unit is None:
        return None

    reasons = _unit_deal_reasons(product, price, baseline_unit=baseline_unit)
    if not reasons:
        return None

    if not _trusted_unit_drop(baseline_unit, listing.price_per_piece):
        return None

    if (
        last_alert_unit is not None
        and abs(last_alert_unit - listing.price_per_piece) < 0.001
    ):
        return None

    return DealAlert(
        product=product,
        price=price,
        reason="; ".join(dict.fromkeys(reasons)),
        baseline_price=mp_state.get("baseline_price"),
        kind="multipack",
        unit_price=listing.price_per_piece,
        unit_label=listing.label,
        target_unit_price=_unit_target(product),
    )
