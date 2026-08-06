import unittest

from bs4 import BeautifulSoup

from src.scrapers.zooroyal import ZooroyalScraper


class ZooroyalScraperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scraper = ZooroyalScraper()
        self.name = (
            "ROYAL CANIN INSTINCTIVE 7+ Nassfutter in Soße für ältere Katzen - 12x85g"
        )
        self.url = (
            "https://www.zooroyal.de/p/royal-canin-instinctive-7-nassfutter-in-sosse-"
            "fuer-aeltere-katzen-12x85g/1000076863/"
        )

    def test_finds_product_inside_product_group(self) -> None:
        data = {
            "@type": "ProductGroup",
            "name": "Royal Canin Instinctive 7+",
            "hasVariant": [
                {
                    "@type": "Product",
                    "name": self.name,
                    "offers": {
                        "@type": "Offer",
                        "price": "15.69",
                        "priceCurrency": "EUR",
                        "availability": "https://schema.org/InStock",
                    },
                }
            ],
        }
        product = self.scraper._find_product_ld(data)
        self.assertIsNotNone(product)
        self.assertEqual(self.scraper._offers_price(product), 15.69)

    def test_html_ignores_du_sparst_savings_badge(self) -> None:
        html = """
        <html><body>
          <h1>ROYAL CANIN INSTINCTIVE 7+ 12x85g</h1>
          <p>Partner 84,00 €</p>
          <p>15,08 € / kg</p>
          <p>Du sparst 5,31 €</p>
          <p>UVP 21,00 €</p>
          <p>15,69 €</p>
          <p>-25%</p>
          <button>In den Warenkorb</button>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        price, original, discount = self.scraper._extract_from_html(
            soup, name=self.name, url=self.url
        )
        self.assertEqual(price, 15.69)
        self.assertEqual(original, 21.0)
        self.assertEqual(discount, 25.0)

    def test_savings_amount_not_plausible_for_12x85(self) -> None:
        self.assertFalse(self.scraper._price_plausible(5.31, self.name, self.url))
        self.assertTrue(self.scraper._price_plausible(15.69, self.name, self.url))

    def test_parse_ld_product_uses_offer_price(self) -> None:
        product = {
            "@type": "Product",
            "name": self.name,
            "offers": {"price": "15.69", "availability": "https://schema.org/InStock"},
        }
        soup = BeautifulSoup("<html><body>Du sparst 5,31 €</body></html>", "html.parser")
        result = self.scraper._parse_ld_product(product, self.url, soup)
        self.assertEqual(result.price, 15.69)


if __name__ == "__main__":
    unittest.main()
