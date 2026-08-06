"""Generate a static deals board from products.yaml + state.json."""
from __future__ import annotations

import argparse
import html
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import load_products
from .models import ProductWatch
from .scrapers import fressnapf, zooplus, zooroyal  # noqa: F401
from .scrapers.base import fetch_price
from .storage import DEFAULT_STATE_PATH, load_state, save_state

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SITE_PATH = ROOT / "docs" / "index.html"

# Extra-Rabatt deals can vanish within hours — only badge fresh checks.
FRESH_DEAL_HOURS = 6


@dataclass
class RetailerPrice:
    retailer: str
    price: Optional[float]
    url: str
    name: str
    is_deal: bool
    last_checked: str = ""
    stale: bool = False

    @property
    def age_label(self) -> str:
        age = _age_hours(self.last_checked)
        if age is None:
            return ""
        if age < 1:
            return "just now"
        if age < 24:
            hours = int(age)
            return f"{hours}h ago"
        days = int(age // 24)
        return f"{days}d ago"


@dataclass
class ProductBoardRow:
    pet: str
    name: str
    pack_size: str
    target_price: Optional[float]
    retailers: List[RetailerPrice]

    @property
    def has_deal(self) -> bool:
        return any(r.is_deal for r in self.retailers)

    @property
    def best_price(self) -> Optional[float]:
        prices = [r.price for r in self.retailers if r.price is not None]
        return min(prices) if prices else None


def _parse_checked(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _age_hours(last_checked: str, *, now: Optional[datetime] = None) -> Optional[float]:
    dt = _parse_checked(last_checked)
    if dt is None:
        return None
    now = now or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 3600.0)


def _is_fresh(last_checked: str, *, now: Optional[datetime] = None) -> bool:
    age = _age_hours(last_checked, now=now)
    if age is None:
        return False
    return age <= FRESH_DEAL_HOURS


def build_board(
    products: List[ProductWatch] | None = None,
    state: Dict[str, Any] | None = None,
    *,
    now: Optional[datetime] = None,
) -> List[ProductBoardRow]:
    products = products if products is not None else load_products()
    state = state if state is not None else load_state()
    now = now or datetime.now(timezone.utc)
    rows: List[ProductBoardRow] = []

    for product in products:
        retailers: List[RetailerPrice] = []
        for retailer in product.retailers:
            key = product.state_key(retailer)
            entry = state.get(key) or {}
            price = entry.get("last_price")
            if isinstance(price, (int, float)):
                price_val: Optional[float] = float(price)
            else:
                price_val = None
            url = (
                entry.get("matched_url")
                or (product.retailer_urls or {}).get(retailer, "")
                or product.url
                or ""
            )
            checked = str(entry.get("last_checked") or "")
            at_target = (
                price_val is not None
                and product.target_price is not None
                and price_val <= product.target_price
            )
            fresh = _is_fresh(checked, now=now)
            retailers.append(
                RetailerPrice(
                    retailer=retailer,
                    price=price_val,
                    url=url,
                    name=entry.get("matched_name") or "",
                    is_deal=at_target and fresh,
                    last_checked=checked,
                    stale=at_target and not fresh,
                )
            )
        rows.append(
            ProductBoardRow(
                pet=product.pet or "Pet",
                name=product.name,
                pack_size=product.pack_size,
                target_price=product.target_price,
                retailers=retailers,
            )
        )

    rows.sort(
        key=lambda row: (
            0 if row.has_deal else 1,
            row.pet.lower(),
            row.name.lower(),
            row.pack_size.lower(),
        )
    )
    return rows


def verify_deal_offers(
    state: Dict[str, Any],
    products: List[ProductWatch] | None = None,
) -> int:
    """Re-scrape URLs that currently look like deals so the site stays accurate."""
    products = products if products is not None else load_products()
    updated = 0
    now = datetime.now(timezone.utc).isoformat()

    for product in products:
        if product.target_price is None:
            continue
        for retailer in product.retailers:
            key = product.state_key(retailer)
            entry = state.get(key) or {}
            price = entry.get("last_price")
            url = entry.get("matched_url") or (product.retailer_urls or {}).get(retailer)
            if not url or not isinstance(price, (int, float)):
                continue
            if float(price) > product.target_price:
                continue
            try:
                result = fetch_price(url)
            except Exception as exc:
                print(f"VERIFY skip [{product.name} @ {retailer}]: {exc}")
                continue
            entry["last_price"] = result.price
            entry["last_checked"] = now
            if result.name:
                entry["matched_name"] = result.name
            entry["matched_url"] = result.url or url
            state[key] = entry
            updated += 1
            print(
                f"VERIFY [{product.name} @ {retailer}] "
                f"€{float(price):.2f} → €{result.price:.2f}"
            )
    return updated


def _fmt_price(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"€{value:.2f}"


def _fmt_checked(rows: List[ProductBoardRow]) -> str:
    stamps = [
        r.last_checked
        for row in rows
        for r in row.retailers
        if r.last_checked
    ]
    if not stamps:
        return "Not checked yet"
    try:
        latest = max(stamps)
        dt = datetime.fromisoformat(latest.replace("Z", "+00:00"))
        local = dt.astimezone()
        return local.strftime("%d %b %Y, %H:%M")
    except ValueError:
        return stamps[-1]


def render_html(rows: List[ProductBoardRow], *, generated_at: Optional[datetime] = None) -> str:
    generated_at = generated_at or datetime.now(timezone.utc)
    deal_count = sum(1 for row in rows if row.has_deal)
    checked = _fmt_checked(rows)
    generated = generated_at.astimezone().strftime("%d %b %Y, %H:%M %Z")

    sections: List[str] = []
    current_pet = None
    for row in rows:
        if row.pet != current_pet:
            current_pet = row.pet
            sections.append(f'<h2 class="pet">{html.escape(current_pet)}</h2>')

        deal_class = " product--deal" if row.has_deal else ""
        target = _fmt_price(row.target_price)
        retailer_bits: List[str] = []
        for offer in row.retailers:
            if offer.is_deal:
                status = "deal"
            elif offer.stale:
                status = "stale"
            elif offer.price is not None:
                status = "ok"
            else:
                status = "miss"
            label = offer.retailer.capitalize()
            price_txt = _fmt_price(offer.price)
            if offer.url:
                price_html = (
                    f'<a class="price-link" href="{html.escape(offer.url)}" '
                    f'target="_blank" rel="noopener noreferrer">{price_txt}</a>'
                )
            else:
                price_html = price_txt
            if offer.is_deal:
                badge = '<span class="badge">deal</span>'
            elif offer.stale:
                badge = '<span class="badge badge--stale">was deal</span>'
            else:
                badge = ""
            age = offer.age_label
            age_html = (
                f'<span class="age" title="{html.escape(offer.last_checked)}">'
                f"{html.escape(age)}</span>"
                if age
                else ""
            )
            retailer_bits.append(
                f'<div class="offer offer--{status}">'
                f'<span class="shop">{html.escape(label)}</span>'
                f'<span class="price">{price_html}{badge}{age_html}</span>'
                f"</div>"
            )

        sections.append(
            f'<article class="product{deal_class}">'
            f'<div class="product__main">'
            f'<h3 class="product__name">{html.escape(row.name)}</h3>'
            f'<p class="product__meta">'
            f'<span>{html.escape(row.pack_size)}</span>'
            f'<span class="dot">·</span>'
            f'<span>target {html.escape(target)}</span>'
            f"</p>"
            f"</div>"
            f'<div class="product__offers">{"".join(retailer_bits)}</div>'
            f"</article>"
        )

    body = "\n".join(sections) if sections else '<p class="empty">No products configured yet.</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Pet Food Deals</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,560;9..144,700&family=Outfit:wght@400;500;600&display=swap" rel="stylesheet" />
  <style>
    :root {{
      --bg0: #e8f0e6;
      --bg1: #d5e4d8;
      --ink: #1c2a22;
      --muted: #5a6b60;
      --line: rgba(28, 42, 34, 0.12);
      --deal: #1f6b45;
      --deal-soft: rgba(31, 107, 69, 0.12);
      --stale: #8a6a2f;
      --miss: #8a9590;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: "Outfit", system-ui, sans-serif;
      background:
        radial-gradient(1200px 600px at 10% -10%, #f7ffe9 0%, transparent 55%),
        radial-gradient(900px 500px at 100% 0%, #cfe3d4 0%, transparent 50%),
        linear-gradient(165deg, var(--bg0), var(--bg1));
    }}
    .wrap {{
      width: min(920px, calc(100% - 2rem));
      margin: 0 auto;
      padding: 2.5rem 0 4rem;
    }}
    .hero {{
      margin-bottom: 2.25rem;
      animation: rise 0.7s ease both;
    }}
    .brand {{
      font-family: "Fraunces", Georgia, serif;
      font-size: clamp(2.4rem, 6vw, 3.6rem);
      font-weight: 700;
      letter-spacing: -0.03em;
      line-height: 1.05;
      margin: 0 0 0.6rem;
    }}
    .lede {{
      margin: 0;
      max-width: 36rem;
      color: var(--muted);
      font-size: 1.05rem;
      line-height: 1.5;
    }}
    .stats {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem 1.25rem;
      margin-top: 1.25rem;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .stats strong {{ color: var(--ink); font-weight: 600; }}
    .pet {{
      font-family: "Fraunces", Georgia, serif;
      font-size: 1.35rem;
      margin: 2rem 0 0.85rem;
      animation: rise 0.6s ease both;
    }}
    .product {{
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 1rem 1.5rem;
      padding: 1rem 0;
      border-top: 1px solid var(--line);
      animation: rise 0.55s ease both;
    }}
    .product:last-child {{ border-bottom: 1px solid var(--line); }}
    .product--deal {{
      background: linear-gradient(90deg, var(--deal-soft), transparent 70%);
      margin: 0 -0.75rem;
      padding-left: 0.75rem;
      padding-right: 0.75rem;
      border-radius: 12px;
      border-top-color: transparent;
    }}
    .product__name {{
      margin: 0;
      font-size: 1.05rem;
      font-weight: 600;
      letter-spacing: -0.01em;
    }}
    .product__meta {{
      margin: 0.35rem 0 0;
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .dot {{ margin: 0 0.35rem; opacity: 0.6; }}
    .product__offers {{
      display: grid;
      gap: 0.45rem;
      align-content: center;
    }}
    .offer {{
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      font-size: 0.95rem;
    }}
    .shop {{ color: var(--muted); min-width: 5.5rem; }}
    .price {{ font-variant-numeric: tabular-nums; font-weight: 500; }}
    .offer--deal .price {{ color: var(--deal); font-weight: 600; }}
    .offer--stale .price {{ color: var(--stale); }}
    .offer--miss .price {{ color: var(--miss); }}
    .price-link {{
      color: inherit;
      text-decoration: none;
      border-bottom: 1px solid transparent;
      transition: border-color 0.2s ease, transform 0.2s ease;
    }}
    .price-link:hover {{ border-bottom-color: currentColor; }}
    .badge {{
      display: inline-block;
      margin-left: 0.45rem;
      padding: 0.08rem 0.4rem;
      border-radius: 999px;
      background: var(--deal);
      color: #f4fff8;
      font-size: 0.68rem;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      vertical-align: middle;
    }}
    .badge--stale {{
      background: transparent;
      color: var(--stale);
      border: 1px solid rgba(138, 106, 47, 0.45);
    }}
    .age {{
      margin-left: 0.45rem;
      color: var(--muted);
      font-size: 0.75rem;
      font-weight: 400;
    }}
    .empty {{ color: var(--muted); }}
    footer {{
      margin-top: 2.5rem;
      color: var(--muted);
      font-size: 0.85rem;
    }}
    @keyframes rise {{
      from {{ opacity: 0; transform: translateY(10px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    @media (max-width: 700px) {{
      .product {{ grid-template-columns: 1fr; gap: 0.75rem; }}
      .wrap {{ padding-top: 1.75rem; }}
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <header class="hero">
      <h1 class="brand">Pet Food Deals</h1>
      <p class="lede">Fresh prices for your watched products. Deal badges only show when the shop was checked within the last {FRESH_DEAL_HOURS} hours — Extra-Rabatt can end anytime.</p>
      <div class="stats">
        <span><strong>{deal_count}</strong> fresh deal{'s' if deal_count != 1 else ''}</span>
        <span>Last shop check: <strong>{html.escape(checked)}</strong></span>
        <span>Page built: <strong>{html.escape(generated)}</strong></span>
      </div>
    </header>
    <section class="board">
      {body}
    </section>
    <footer>Telegram alerts still fire on new deals. Prices are re-checked about every 3 hours; open a link soon after a fresh deal badge.</footer>
  </main>
</body>
</html>
"""


def write_site(
    path: Path | None = None,
    *,
    products: List[ProductWatch] | None = None,
    state: Dict[str, Any] | None = None,
    verify_deals: bool = False,
    state_path: Path | None = None,
) -> Path:
    out = path or DEFAULT_SITE_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    products = products if products is not None else load_products()
    state = state if state is not None else load_state(state_path)
    if verify_deals:
        changed = verify_deal_offers(state, products)
        if changed:
            save_state(state, state_path)
            print(f"Verified {changed} deal offer(s)")
    rows = build_board(products=products, state=state)
    out.write_text(render_html(rows), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the pet food deals website")
    parser.add_argument(
        "--verify-deals",
        action="store_true",
        help="Re-scrape current deal URLs before building the page",
    )
    args = parser.parse_args()
    path = write_site(verify_deals=args.verify_deals)
    rows = build_board()
    deals = sum(1 for row in rows if row.has_deal)
    print(f"Wrote {path} ({len(rows)} products, {deals} fresh deals)")


if __name__ == "__main__":
    main()
