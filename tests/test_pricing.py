"""Run: python -m unittest tests.test_pricing -v"""
import unittest

from src.pricing import same_item_size, target_unit_price, unit_pricing


class TestPricing(unittest.TestCase):
    def test_unit_price_12x85g(self):
        u = unit_pricing("12x85g", 15.0)
        self.assertIsNotNone(u)
        assert u is not None
        self.assertEqual(u.price_per_piece, 1.25)
        self.assertEqual(u.pack_count, 12)

    def test_unit_price_48x85g(self):
        u = unit_pricing("48x85g", 48.0)
        self.assertIsNotNone(u)
        assert u is not None
        self.assertEqual(u.price_per_piece, 1.0)

    def test_target_unit_from_yaml_pack(self):
        self.assertEqual(target_unit_price(15.0, "12x85g"), 1.25)

    def test_same_item_size_different_count(self):
        self.assertTrue(same_item_size("12x85g", "48x85g"))
        self.assertFalse(same_item_size("12x85g", "12x400g"))


if __name__ == "__main__":
    unittest.main()
