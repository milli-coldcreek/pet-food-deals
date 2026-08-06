import unittest
from datetime import datetime, timedelta, timezone

from src.models import ProductWatch
from src.site import FRESH_DEAL_HOURS, build_board, render_html, write_site


def _fresh_iso(hours_ago: float = 0.5) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


class SiteBoardTests(unittest.TestCase):
    def test_deal_flagged_when_price_at_or_below_target(self) -> None:
        products = [
            ProductWatch(
                name="Royal Canin Instinctive in Soße",
                search_query="Royal Canin Instinctive in Soße",
                pack_size="12x85g",
                pet="Cats",
                target_price=15.0,
                retailers=["zooplus", "fressnapf"],
            )
        ]
        state = {
            "royal-canin-instinctive-in-so-e|12x85g|zooplus": {
                "last_price": 12.39,
                "matched_url": "https://www.zooplus.de/example",
                "matched_name": "RC",
                "last_checked": _fresh_iso(),
            },
            "royal-canin-instinctive-in-so-e|12x85g|fressnapf": {
                "last_price": 16.49,
                "last_checked": _fresh_iso(),
            },
        }
        rows = build_board(products, state)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0].has_deal)
        self.assertEqual(rows[0].best_price, 12.39)
        zooplus = next(r for r in rows[0].retailers if r.retailer == "zooplus")
        self.assertTrue(zooplus.is_deal)
        fressnapf = next(r for r in rows[0].retailers if r.retailer == "fressnapf")
        self.assertFalse(fressnapf.is_deal)

    def test_old_deal_is_stale_not_badged(self) -> None:
        products = [
            ProductWatch(
                name="Feringa Classic Meat Menü",
                search_query="Feringa Classic Meat Menü",
                pack_size="24x400g",
                pet="Cats",
                target_price=40.0,
                retailers=["zooplus"],
            )
        ]
        state = {
            "feringa-classic-meat-men|24x400g|zooplus": {
                "last_price": 32.19,
                "matched_url": "https://www.zooplus.de/feringa",
                "last_checked": _fresh_iso(hours_ago=FRESH_DEAL_HOURS + 2),
            }
        }
        rows = build_board(products, state)
        offer = rows[0].retailers[0]
        self.assertFalse(offer.is_deal)
        self.assertTrue(offer.stale)
        html = render_html(rows)
        self.assertIn("was deal", html)
        self.assertNotIn('class="badge">deal</span>', html)

    def test_html_includes_product_and_deal_badge(self) -> None:
        products = [
            ProductWatch(
                name="Feringa Classic Meat Menü",
                search_query="Feringa Classic Meat Menü",
                pack_size="24x400g",
                pet="Cats",
                target_price=40.0,
                retailers=["zooplus"],
            )
        ]
        state = {
            "feringa-classic-meat-men|24x400g|zooplus": {
                "last_price": 32.19,
                "matched_url": "https://www.zooplus.de/feringa",
                "last_checked": _fresh_iso(),
            }
        }
        html = render_html(build_board(products, state))
        self.assertIn("Pet Food Deals", html)
        self.assertIn("Feringa Classic Meat Menü", html)
        self.assertIn("€32.19", html)
        self.assertIn("deal", html)

    def test_write_site_creates_file(self) -> None:
        from pathlib import Path
        import tempfile

        products = [
            ProductWatch(
                name="Test Food",
                search_query="Test Food",
                pack_size="6x100g",
                pet="Cats",
                target_price=7.0,
                retailers=["zooplus"],
            )
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "index.html"
            write_site(out, products=products, state={})
            self.assertTrue(out.exists())
            self.assertIn("Test Food", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
