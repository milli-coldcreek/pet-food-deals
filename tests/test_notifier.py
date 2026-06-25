import unittest

from src.models import DealAlert, PriceResult, ProductWatch
from src.notifier import format_deal_message


class FormatDealMessageTests(unittest.TestCase):
    def _alert(self, **kwargs) -> DealAlert:
        product = ProductWatch(
            name="Royal Canin Instinctive in Soße",
            search_query="Royal Canin Instinctive in Soße",
            pack_size="12x85g",
            pet="Cats",
            target_price=15.0,
        )
        price = PriceResult(
            name="Royal Canin Instinctive 12 x 85 g",
            price=12.39,
            url="https://www.zooplus.de/example",
            retailer="zooplus",
            original_price=15.49,
        )
        defaults = {
            "product": product,
            "price": price,
            "reason": "target price",
            "baseline_price": 15.49,
        }
        defaults.update(kwargs)
        return DealAlert(**defaults)

    def test_short_three_line_format(self):
        msg = format_deal_message(self._alert())
        self.assertEqual(
            msg,
            "\n".join(
                [
                    "Cats — Royal Canin Instinctive in Soße",
                    "€12.39",
                    "https://www.zooplus.de/example",
                ]
            ),
        )

    def test_out_of_stock_note_on_price_line(self):
        alert = self._alert()
        alert.price.in_stock = False
        msg = format_deal_message(alert)
        self.assertIn("€12.39 (out of stock)", msg.splitlines()[1])


if __name__ == "__main__":
    unittest.main()
