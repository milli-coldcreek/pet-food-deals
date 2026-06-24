from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .matching import PackSize, parse_pack_size, same_item_size, same_item_size_in_listing


@dataclass(frozen=True)
class UnitPricing:
    """Normalized price for one item in a multipack (e.g. one 85 g pouch)."""

    pack_count: int
    item_amount: float
    item_unit: str
    total_price: float
    price_per_piece: float
    price_per_kg: Optional[float] = None

    @property
    def label(self) -> str:
        amount = int(self.item_amount) if self.item_amount == int(self.item_amount) else self.item_amount
        return f"{self.pack_count}x{amount}{self.item_unit}"


def unit_pricing(pack_size: str, total_price: float) -> Optional[UnitPricing]:
    pack = parse_pack_size(pack_size)
    if pack is None or pack.count <= 0 or total_price < 0:
        return None

    per_piece = total_price / pack.count
    per_kg = None
    if pack.unit == "g" and pack.amount > 0:
        total_g = pack.count * pack.amount
        per_kg = total_price / total_g * 1000

    return UnitPricing(
        pack_count=pack.count,
        item_amount=pack.amount,
        item_unit=pack.unit,
        total_price=total_price,
        price_per_piece=per_piece,
        price_per_kg=per_kg,
    )


def unit_pricing_from_texts(total_price: float, *texts: str) -> Optional[UnitPricing]:
    for text in texts:
        if not text:
            continue
        pack = parse_pack_size(text)
        if pack is not None:
            return unit_pricing(f"{pack.count}x{pack.amount}{pack.unit}", total_price)
    return None


def target_unit_price(target_total: float, reference_pack: str) -> Optional[float]:
    pricing = unit_pricing(reference_pack, target_total)
    return pricing.price_per_piece if pricing else None


def format_unit_price(pricing: UnitPricing) -> str:
    return f"€{pricing.price_per_piece:.2f}/piece ({pricing.label})"
