import unittest

from src.deals import (
    MAX_TRUSTED_DROP_PCT,
    _trusted_price_drop,
    _trusted_unit_drop,
    evaluate_multipack_deal,
)
from src.models import PriceResult, ProductWatch


class TrustedDropTests(unittest.TestCase):
    def test_rejects_implausible_total_drop(self) -> None:
        self.assertFalse(_trusted_price_drop(30.0, 9.93))

    def test_allows_normal_sale(self) -> None:
        self.assertTrue(_trusted_price_drop(15.49, 12.39))

    def test_rejects_implausible_unit_drop(self) -> None:
        self.assertFalse(_trusted_unit_drop(2.83, 1.66))

    def test_allows_small_unit_drop(self) -> None:
        self.assertTrue(_trusted_unit_drop(2.83, 2.55))


class TargetGatingTests(unittest.TestCase):
    def test_multipack_skips_baseline_drop_above_target(self) -> None:
        product = ProductWatch(
            name="Feringa Classic Meat Menü",
            search_query="Feringa",
            pack_size="12x400g",
            pet="Cats",
            target_price=20.0,
            retailers=["zooplus"],
        )
        price = PriceResult(
            name="Sparpaket Feringa Classic Meat Menü 24 x 400 g",
            price=43.99,
            url="https://www.zooplus.de/shop/x?activeVariant=1244114.5",
            retailer="zooplus",
        )
        mp_state = {
            "baseline_price": 49.96,
            "baseline_unit_price": 2.0816666666666666,
            "pack_label": "24x400g",
        }
        alert = evaluate_multipack_deal(
            product, price, mp_state, primary_on_deal=False
        )
        self.assertIsNone(alert)


if __name__ == "__main__":
    unittest.main()
