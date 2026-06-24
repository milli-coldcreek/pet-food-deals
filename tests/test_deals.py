import unittest

from src.deals import MAX_TRUSTED_DROP_PCT, _trusted_price_drop, _trusted_unit_drop


class TrustedDropTests(unittest.TestCase):
    def test_rejects_implausible_total_drop(self) -> None:
        self.assertFalse(_trusted_price_drop(30.0, 9.93))

    def test_allows_normal_sale(self) -> None:
        self.assertTrue(_trusted_price_drop(15.49, 12.39))

    def test_rejects_implausible_unit_drop(self) -> None:
        self.assertFalse(_trusted_unit_drop(2.83, 1.66))

    def test_allows_small_unit_drop(self) -> None:
        self.assertTrue(_trusted_unit_drop(2.83, 2.55))


if __name__ == "__main__":
    unittest.main()
